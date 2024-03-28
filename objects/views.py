from __future__ import annotations

from enum import Enum
from math import floor
from typing import Optional, TYPE_CHECKING

from discord import Interaction, ButtonStyle, SelectOption, Embed, File, Message
from discord.ui import View, Button, Select, Modal, TextInput

from objects.color import Palette
from objects.coordinates import Coordinates, BoundingBox
from objects.frame import CustomFrame
from sql.sqlManager import SQLManager

if TYPE_CHECKING:
    from cogs.canvas import CanvasCog


class ConfirmEnum(Enum):
    CONFIRM = "confirm"
    CANCEL = "cancel"


class NavigationEnum(Enum):
    LEFT = Coordinates(-1, 0)
    RIGHT = Coordinates(1, 0)
    UP = Coordinates(0, -1)
    DOWN = Coordinates(0, 1)


class ConfirmView(View):
    def __init__(self, user_id: int, *, timeout=None):
        super().__init__(timeout=30 if timeout is None else timeout)
        self.user_id = user_id
        self.confirm: Optional[ConfirmEnum] = None

        self.interaction: Optional[Interaction] = None

    class ConfirmViewButton(Button):
        def __init__(self, output: ConfirmEnum, **kwargs):
            super().__init__(**kwargs)
            self.output = output

        async def callback(self, interaction: Interaction):
            self.view.interaction = interaction
            self.view.confirm = self.output
            self.view.stop()

    def confirm_button(self, **kwargs):
        return self.ConfirmViewButton(
            ConfirmEnum.CONFIRM,
            emoji="<:blorpletick:436007034471710721>",
            style=ButtonStyle.green,
            custom_id="confirm",
            **kwargs,
        )

    def cancel_button(self, **kwargs):
        return self.ConfirmViewButton(
            ConfirmEnum.CANCEL,
            emoji="<:blorplecross:436007034832551938>",
            style=ButtonStyle.red,
            custom_id="cancel",
            **kwargs,
        )

    async def update_view(self):
        await self.interaction.response.edit_message(view=self)

    async def defer(self):
        await self.interaction.response.defer()

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id


class EditModal(Modal):
    def __init__(
        self,
        user_id: int,
        inputs: dict[str, TextInput],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.user_id = user_id

        self.inputs = inputs
        for text_input in inputs.values():
            self.add_item(text_input)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.defer()

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id

    def __getitem__(self, item):
        return self.inputs[item].value


class NavigateView(ConfirmView):
    def __init__(
        self,
        *args,
        disabled_directions: Optional[list[NavigationEnum]] = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.direction: Optional[NavigationEnum] = None

        disabled = lambda direction: (
            direction in disabled_directions if disabled_directions else False
        )

        self.add_item(self.confirm_button(row=0))
        self.add_item(
            self.NavigateViewButton(
                NavigationEnum.UP,
                custom_id="up",
                emoji="⬆️",
                row=0,
                disabled=disabled(NavigationEnum.UP),
            )
        )
        self.add_item(self.cancel_button(row=0))

        self.add_item(
            self.NavigateViewButton(
                NavigationEnum.LEFT,
                custom_id="left",
                emoji="⬅️",
                row=1,
                disabled=disabled(NavigationEnum.LEFT),
            )
        )
        self.add_item(
            self.NavigateViewButton(
                NavigationEnum.DOWN,
                custom_id="down",
                emoji="⬇️",
                row=1,
                disabled=disabled(NavigationEnum.DOWN),
            )
        )
        self.add_item(
            self.NavigateViewButton(
                NavigationEnum.RIGHT,
                custom_id="right",
                emoji="➡️",
                row=1,
                disabled=disabled(NavigationEnum.RIGHT),
            )
        )

    class NavigateViewButton(Button):
        def __init__(self, output: NavigationEnum, **kwargs):
            super().__init__(**kwargs)
            self.output = output

        async def callback(self, interaction: Interaction):
            self.view.interaction = interaction
            self.view.direction = self.output
            self.view.stop()


class PaletteView(ConfirmView):
    def __init__(self, palette: Palette, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.palette: Palette = palette

        self.dropdown = self.PaletteSelect(palette, row=0)
        self.add_item(self.dropdown)
        self.add_item(self.confirm_button(row=1))
        self.add_item(self.cancel_button(row=1))

    class PaletteSelect(Select):
        def __init__(self, palette: Palette, **kwargs):
            self.palette: Palette = palette

            options = [
                SelectOption(
                    label=color.name, value=str(color.id), emoji=color.emoji_formatted
                )
                for color in self.palette.sorted()
            ]

            super().__init__(
                placeholder="Select a color",
                options=options,
                min_values=1,
                max_values=1,
                **kwargs,
            )

        async def callback(self, interaction: Interaction):
            await interaction.response.defer()


class FrameEditView(ConfirmView):
    def __init__(
        self,
        frame: CustomFrame,
        base_embed: Embed,
        *,
        max_size_percentage: float = 0.25,
        message: Message = None,
        canvas_cog: CanvasCog = None,
        **kwargs,
    ):
        super().__init__(timeout=300, **kwargs)
        self.frame = frame
        self.base_embed = base_embed
        self.message = message
        self.canvas_cog = canvas_cog
        self.max_size_percentage = max_size_percentage

        self.error = None

        self.embed: Embed = self.to_embed()
        self.file: Optional[File] = None

        self.update_view_contents()

    def update_view_contents(self):
        self.clear_items()

        self.add_item(self.EditButton(row=0))

        self.add_item(self.cancel_button(row=0))
        self.add_item(self.confirm_button(row=0, disabled=not self.frame.is_complete))

    def update_message_contents(self):
        self.embed = self.to_embed()
        self.file = None

    async def update_message_contents_with_image(self):
        self.embed, self.file = await self.to_embed_with_image()

    async def update_message(self):
        self.update_view_contents()
        await self.update_message_contents_with_image()
        contents = {
            "embed": self.embed,
            "view": self,
        }
        if self.file:
            contents["attachments"] = [self.file]
        if self.message is None:
            await self.interaction.response.edit_message(**contents)
        else:
            await self.message.edit(**contents)

    def to_embed(self) -> Embed:
        embed = self.base_embed.copy()
        embed.description = (
            f"**Name:** {self.frame.name or ''}\n"
            f"**Coordinates:** {self.frame.bbox if self.frame.bbox else ''}\n"
            f"\n"
            f"> *Tip: Coordinates are specified by the top-left `(x0, y0)` and bottom-right `(x1, y1)` corners.*\n"
            + (f"\n{self.error}" if self.error else "")
        )
        return embed

    async def to_embed_with_image(self) -> tuple[Embed, Optional[File]]:
        embed = self.to_embed()
        if not self.canvas_cog or not self.frame.bbox:
            return embed, None
        sql: SQLManager = await self.canvas_cog.sql()
        await self.frame.load_pixels(sql)
        await sql.close()
        file, file_name, size_bytes = await self.canvas_cog.async_image(
            self.frame.generate_image,
            max_size=Coordinates(512, 512),
            file_name=f"frame.png",
        )
        embed.set_image(url=file_name)
        return embed, file

    class EditButton(Button):
        def __init__(self, **kwargs):
            super().__init__(label="Edit values", **kwargs)

        async def callback(self, interaction: Interaction):
            modal = EditModal(
                interaction.user.id,
                inputs={
                    "name": TextInput(
                        label="Name",
                        default=self.view.frame.name or "",
                        min_length=1,
                        max_length=32,
                        custom_id="name",
                        required=True,
                    ),
                    "x0": TextInput(
                        label="Left border (x0)",
                        default=(
                            str(self.view.frame.bbox.x0) if self.view.frame.bbox else ""
                        ),
                        max_length=5,
                        custom_id="x0",
                        required=True,
                    ),
                    "y0": TextInput(
                        label="Top border (y0)",
                        default=(
                            str(self.view.frame.bbox.y0) if self.view.frame.bbox else ""
                        ),
                        max_length=5,
                        custom_id="y0",
                        required=True,
                    ),
                    "x1": TextInput(
                        label="Right border (x1)",
                        default=(
                            str(self.view.frame.bbox.x1) if self.view.frame.bbox else ""
                        ),
                        max_length=5,
                        custom_id="x1",
                        required=True,
                    ),
                    "y1": TextInput(
                        label="Bottom border (y1)",
                        default=(
                            str(self.view.frame.bbox.y1) if self.view.frame.bbox else ""
                        ),
                        max_length=5,
                        custom_id="y1",
                        required=True,
                    ),
                },
                title="Edit values - (x0, y0)-(x1, y1)",
                timeout=300,
                custom_id="edit",
            )
            await interaction.response.send_modal(modal)
            await modal.wait()

            self.view.frame.name = modal["name"]
            try:
                bbox = BoundingBox.from_coordinates(
                    int(modal["x0"]),
                    int(modal["y0"]),
                    int(modal["x1"]),
                    int(modal["y1"]),
                )
                if bbox not in self.view.frame.canvas.bbox:
                    self.view.error = (
                        f"Invalid coordinates. "
                        f"Please ensure the frame is within the canvas {self.view.frame.canvas.bbox}."
                    )

                elif bbox.width < 5 or bbox.height < 5:
                    self.view.error = (
                        "Invalid coordinates. Please ensure the frame is at least 5x5."
                    )

                elif (
                    self.view.frame.canvas.bbox_percentage(bbox)
                    > self.view.max_size_percentage
                ):
                    rough = floor(
                        (
                            self.view.frame.canvas.bbox.area
                            * self.view.max_size_percentage
                        )
                        ** 0.5
                    )
                    self.view.error = (
                        f"Invalid coordinates. "
                        f"The frame must not exceed {self.view.max_size_percentage * 100:.0f}% of the canvas "
                        f"(around {rough}x{rough})."
                    )

                else:
                    self.view.frame.bbox = bbox
                    self.view.error = None
            except ValueError:
                self.view.error = "Invalid coordinates. Please specify digits only."

            await self.view.update_message()
