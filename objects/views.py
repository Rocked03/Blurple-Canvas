from __future__ import annotations

import re
from copy import copy
from enum import Enum
from math import floor
from typing import Optional, TYPE_CHECKING, Callable, Type

from discord import (
    Interaction,
    ButtonStyle,
    SelectOption,
    Embed,
    File,
    Message,
    Role,
    Invite,
    NotFound,
    InteractionResponseType,
    HTTPException,
    InteractionResponded,
)
from discord.ui import View, Button, Select, Modal, TextInput, Item

from objects.color import Palette, Color
from objects.coordinates import Coordinates, BoundingBox
from objects.frame import CustomFrame
from objects.style import Styles, Style
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
    def __init__(
        self,
        user_id: int = None,
        *,
        timeout=None,
    ):
        super().__init__(timeout=30 if timeout is None else timeout)
        self.user_id = user_id
        self.confirm: Optional[ConfirmEnum] = None

        self.interaction: Optional[Interaction] = None

    @property
    def is_complete(self) -> bool:
        return self.confirm == ConfirmEnum.CONFIRM

    @property
    def is_cancelled(self) -> bool:
        return self.confirm == ConfirmEnum.CANCEL

    class ConfirmViewButton(Button):
        def __init__(self, output: ConfirmEnum, **kwargs):
            super().__init__(**kwargs)
            self.output = output

        async def callback(self, interaction: Interaction):
            self.view.interaction = interaction
            self.view.confirm = self.output
            self.view.stop()

    def confirm_button(
        self,
        *,
        label: str = None,
        emoji: str = "<:blorpletick:436007034471710721>",
        **kwargs,
    ) -> Button:
        return self.ConfirmViewButton(
            ConfirmEnum.CONFIRM,
            label=label,
            emoji=emoji,
            style=ButtonStyle.green,
            custom_id="confirm",
            **kwargs,
        )

    def cancel_button(
        self,
        *,
        label: str = None,
        emoji: str = "<:blorplecross:436007034832551938>",
        **kwargs,
    ) -> Button:
        return self.ConfirmViewButton(
            ConfirmEnum.CANCEL,
            label=label,
            emoji=emoji,
            style=ButtonStyle.red,
            custom_id="cancel",
            **kwargs,
        )

    async def update_view(self) -> None:
        await self.interaction.response.edit_message(view=self)

    async def defer(self) -> None:
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

        self.interaction: Optional[Interaction] = None

        self.inputs = inputs
        for text_input in inputs.values():
            self.add_item(text_input)

    async def on_submit(self, interaction: Interaction) -> None:
        self.interaction = interaction

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id

    def __getitem__(self, item) -> str:
        return self.inputs[item].value


class Paginator:
    def __init__(
        self, *, user_id: int = None, base_embed: Callable[..., Embed] = None
    ) -> None:
        self.pages: list[PaginatorView] = []
        self.add_page(StartPagePaginatorView(self.pages))

        self.user_id = user_id
        self.base_embed = base_embed

        self.page = 0

    def add_page(self, page: PaginatorView) -> None:
        self.pages.append(page)

    @property
    def current_page(self) -> PaginatorView:
        return self.pages[self.page]

    @property
    def max_page(self) -> int:
        return len(self.pages) - 1

    def assign_pages(self) -> None:
        self.add_page(EndPagePaginatorView(self.pages))

        for i, page in enumerate(self.pages):
            page.page_state = (
                PageStage.START
                if i == 0
                else PageStage.END if i == self.max_page else PageStage.MIDDLE
            )
            if page.user_id is None:
                page.user_id = self.user_id
            if page.base_embed is None:
                page.base_embed = self.base_embed

    async def start(self, interaction: Interaction) -> bool:
        self.assign_pages()

        view: Optional[PaginatorView] = None
        msg: Optional[Message] = None
        while self.page <= self.max_page:
            view = self.current_page
            view.interaction = interaction
            view.msg = msg
            await view.update_message()
            timeout = await view.wait()

            if timeout or view.is_cancelled:
                view.stop()
                if view.is_cancelled:
                    await view.update_message_cancel()
                    return False
                elif timeout:
                    await view.update_message_cancel("Timed out.")
                    return False

            if view.is_complete:
                msg = view.msg
                interaction = view.interaction
                self.page += 1

        await view.update_message_complete()
        view.stop()
        return True


class PageStage(Enum):
    START = 0
    MIDDLE = 1
    END = 2


class PaginatorView(ConfirmView):
    def __init__(
        self,
        base_embed: Callable[..., Embed] = None,
        *args,
        msg: Message = None,
        **kwargs,
    ):
        super().__init__(timeout=300, *args, **kwargs)

        self.items: list[Item] = []
        self.embed: Optional[Embed] = None

        self.base_embed = base_embed

        self.complete = False
        self.optional = True
        self.page_state: PageStage = PageStage.MIDDLE
        self.interaction: Optional[Interaction] = None

        self.description_embed_field: dict[str, str] = {}

        self.msg: Optional[Message] = msg

    @property
    def description_as_embed_field(self) -> dict[str, str]:
        return {
            "name": self.description_embed_field["name"]
            + (" (Optional)" if self.optional else ""),
            "value": self.description_embed_field["value"],
        }

    def update_view_contents(self) -> None:
        self.check()

        self.clear_items()

        for item in self.items:
            self.add_item(item)

        self.add_item(
            self.ConfirmViewButton(
                ConfirmEnum.CANCEL,
                label="Cancel",
                style=ButtonStyle.red,
                custom_id="cancel",
                row=4,
            )
        )

        self.add_item(
            self.ConfirmViewButton(
                ConfirmEnum.CONFIRM,
                label=(
                    "Finish"
                    if self.page_state == PageStage.END
                    else ("Next" if self.complete or not self.optional else "Skip")
                ),
                style=ButtonStyle.green,
                custom_id="next",
                disabled=not (self.complete or self.optional),
                row=4,
            )
        )

    def check(self) -> bool:
        self.complete = True
        return True

    def update_message_contents(self) -> None:
        self.embed = self.to_embed()

    def to_embed(self) -> Embed:
        raise NotImplementedError

    def result_embed_field(self) -> dict[str, str]:
        raise NotImplementedError

    async def update_message(self) -> None:
        self.update_view_contents()
        self.update_message_contents()

        await self.do_update_message()

    async def update_message_cancel(self, text="Cancelled") -> None:
        self.embed.title = text
        self.clear_items()
        await self.do_update_message()

    async def update_message_complete(self, text="Complete") -> None:
        self.embed.title = text
        self.clear_items()
        await self.do_update_message()

    async def do_update_message(self) -> None:

        try:
            await self.interaction.response.edit_message(embed=self.embed, view=self)
        except (HTTPException, InteractionResponded):
            if not self.msg:
                self.msg = await self.interaction.followup.send(
                    embed=self.embed, view=self, wait=True
                )
            else:
                await self.interaction.followup.edit_message(
                    self.msg.id, embed=self.embed, view=self
                )


class StartPagePaginatorView(PaginatorView):
    def __init__(self, pages: list[PaginatorView], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = pages

    def to_embed(self) -> Embed:
        embed = self.base_embed(user=self.interaction.user, title="Starting Setup")
        embed.description = (
            "The following pages will include these settings below. "
            "Please have these ready before continuing."
        )
        for page in self.pages:
            if isinstance(page, StartPagePaginatorView) or isinstance(
                page, EndPagePaginatorView
            ):
                continue
            embed.add_field(**page.description_as_embed_field)
        return embed


class EndPagePaginatorView(PaginatorView):
    def __init__(self, pages: list[PaginatorView], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = pages

    def to_embed(self) -> Embed:
        embed = self.base_embed(user=self.interaction.user, title="Confirming Setup")
        for page in self.pages:
            if isinstance(page, StartPagePaginatorView) or isinstance(
                page, EndPagePaginatorView
            ):
                continue
            embed.add_field(**page.result_embed_field())
        return embed


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

        self.style = Styles.get_style()
        self.embed: Embed = self.to_embed()
        self.file: Optional[File] = None

        self.update_view_contents()

    def update_view_contents(self):
        self.clear_items()

        self.add_item(self.EditButton(row=0))
        self.add_item(self.StyleSelect(self.style, row=1))

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
            f"**Style:** {self.style.name}\n"
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
        self.frame.set_style(self.style.id)
        file, file_name, size_bytes = await self.canvas_cog.async_image(
            self.frame.generate_image,
            max_size=Coordinates(1000, 1000),
            file_name=f"frame.png",
        )
        embed.set_image(url=file_name)
        return embed, file

    class EditButton(Button):
        def __init__(self, **kwargs):
            super().__init__(label="Edit values", **kwargs)

        def modal(self, user_id: int) -> EditModal:
            common_params = {
                "max_length": 5,
                "required": True,
            }
            bbox = self.view.frame.bbox if self.view.frame.bbox else {}

            return EditModal(
                user_id,
                inputs={
                    "name": TextInput(
                        label="Name",
                        default=self.view.frame.name or "",
                        min_length=1,
                        max_length=32,
                        custom_id="name",
                        required=True,
                    ),
                    **{
                        key: TextInput(
                            label=label,
                            default=str(bbox.get(key[0], "")),
                            custom_id=key,
                            **common_params,
                        )
                        for key, label in [
                            ("x0", "Left border (x0)"),
                            ("y0", "Top border (y0)"),
                            ("x1", "Right border (x1)"),
                            ("y1", "Bottom border (y1)"),
                        ]
                    },
                },
                title="Edit values - (x0, y0)-(x1, y1)",
                timeout=300,
                custom_id="edit",
            )

        async def callback(self, interaction: Interaction):
            modal = self.modal(interaction.user.id)
            await interaction.response.send_modal(modal)
            await modal.wait()

            await modal.interaction.response.defer()

            self.view.frame.name = modal["name"]
            try:
                bbox = BoundingBox.from_coordinates(
                    int(modal["x0"]),
                    int(modal["y0"]),
                    int(modal["x1"]),
                    int(modal["y1"]),
                )
                canvas_bbox = self.view.frame.canvas.bbox
                if (
                    bbox not in canvas_bbox
                    or bbox.min_dimension < 5
                    or self.view.frame.canvas.bbox_percentage(bbox)
                    > self.view.max_size_percentage
                ):
                    self.view.error = (
                        f"Invalid coordinates. "
                        f"Please ensure the frame is within the canvas {canvas_bbox}."
                        if bbox not in canvas_bbox
                        else (
                            "Invalid coordinates. Please ensure the frame is at least 5x5."
                            if bbox.min_dimension < 5
                            else f"Invalid coordinates. The frame must not exceed "
                            f"{self.view.max_size_percentage * 100:.0f}% of the canvas."
                        )
                    )

                else:
                    self.view.frame.bbox = bbox
                    self.view.error = None
            except ValueError:
                self.view.error = "Invalid coordinates. Please specify digits only."

            await self.view.update_message()

    class StyleSelect(Select):
        def __init__(self, selected_style: Type[Style] = None, **kwargs):
            options = [
                SelectOption(
                    label=style.name,
                    value=str(style_id),
                    default=style == selected_style,
                )
                for style_id, style in Styles.get_styles().items()
            ]
            super().__init__(
                placeholder="Select a style",
                options=options,
                min_values=1,
                max_values=1,
                **kwargs,
            )

        async def callback(self, interaction: Interaction):
            self.view.style = Styles.get_style(int(self.values[0]))
            await interaction.response.defer()
            await self.view.update_message()


class SetupManagerRoleView(PaginatorView):
    def __init__(self, role: Role = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role: Optional[Role] = role
        self.role_id_or_name: Optional[str] = None if not self.role else role.id

        self.items.append(self.EditButton(row=0))

        self.description_embed_field = {
            "name": "Manager Role",
            "value": "The role that will be used to manage your server's canvas settings.",
        }

    def to_embed(self):
        embed = self.base_embed(user=self.interaction.user, title="Select Manager Role")

        embed.description = "Please select the role that will be used to manage your server's canvas settings."

        embed.add_field(
            name="Manager Role",
            value=(
                self.role.mention
                if self.role
                else (
                    "None"
                    if self.role_id_or_name is None
                    else f"`{self.role_id_or_name}` is an invalid role name/ID."
                )
            ),
        )

        return embed

    def result_embed_field(self) -> dict[str, str]:
        return {
            "name": "Manager Role",
            "value": self.role.mention if self.complete else "Skipped",
        }

    def check(self) -> bool:
        self.complete = self.role is not None
        return self.complete

    def check_role(self):
        role = next(
            (
                role
                for role in self.interaction.guild.roles
                if (
                    self.role_id_or_name.isdigit()
                    and role.id == int(self.role_id_or_name)
                )
                or role.name.lower() == self.role_id_or_name.lower().strip()
            ),
            None,
        )
        if role:
            self.role = role

    class EditButton(Button):
        def __init__(self, **kwargs):
            super().__init__(label="Edit role", **kwargs)

        @property
        def role_id_or_name(self) -> str:
            return (
                str(self.view.role_id_or_name).strip()
                if self.view.role_id_or_name
                else None
            )

        async def callback(self, interaction: Interaction):
            modal = EditModal(
                interaction.user.id,
                inputs={
                    "role": TextInput(
                        label="Role name or ID",
                        custom_id="role",
                        required=True,
                        default=self.role_id_or_name or None,
                    )
                },
                title="Manager Role",
                custom_id="edit",
            )
            await interaction.response.send_modal(modal)
            await modal.wait()

            self.view.interaction = modal.interaction

            self.view.role_id_or_name = modal["role"]
            self.view.check_role()

            await self.view.update_message()


class SetupInviteView(PaginatorView):
    def __init__(self, invite: Invite = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.invite_obj: Optional[Invite] = invite
        self.invite: Optional[str] = None if not self.invite_obj else invite.url

        self.description_embed_field = {
            "name": "Invite",
            "value": "A permanent invite link that will be used to invite users to your server.",
        }

        self.items.append(self.EditButton(row=0))

    def to_embed(self):
        embed = self.base_embed(user=self.interaction.user, title="Invite")

        embed.description = "Please enter a permanent invite link that will be used to invite users to your server."

        embed.add_field(
            name="Invite",
            value=(
                (
                    self.invite_obj
                    if self.check()
                    else f"{self.invite_obj} is not valid - please provide a permanent server invite for this server."
                )
                if self.invite_obj
                else (
                    "None"
                    if self.invite is None
                    else f"`{self.invite}` is not a valid invite link."
                )
            ),
        )

        return embed

    def result_embed_field(self) -> dict[str, str]:
        return {
            "name": "Invite",
            "value": self.invite_obj.url if self.complete else "Skipped",
        }

    def check(self) -> bool:
        self.complete = (
            self.invite_obj is not None
            and self.invite_obj.guild.id == self.interaction.guild.id
            and self.invite_obj.expires_at is None
        )
        return self.complete

    async def check_invite(self):
        try:
            self.invite_obj = await self.interaction.client.fetch_invite(self.invite)
        except NotFound:
            self.invite_obj = None

    class EditButton(Button):
        def __init__(self, **kwargs):
            super().__init__(label="Edit Invite", **kwargs)

        @property
        def invite(self):
            return (
                self.view.invite_obj.url
                if self.view.invite_obj
                else (self.view.invite.strip() if self.view.invite else None)
            )

        async def callback(self, interaction: Interaction):
            modal = EditModal(
                interaction.user.id,
                inputs={
                    "invite": TextInput(
                        label="Invite link",
                        custom_id="invite",
                        required=True,
                        default=self.invite or None,
                    )
                },
                title="Invite",
                custom_id="edit",
            )
            await interaction.response.send_modal(modal)
            await modal.wait()

            self.view.interaction = modal.interaction

            self.view.invite = modal["invite"]
            await self.view.check_invite()

            await self.view.update_message()


class SetupCustomColorView(PaginatorView):
    def __init__(self, palette: Palette = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.create: bool = False
        self.color: Optional[Color] = None

        self.create_color: dict[str, Optional[str]] = {
            "name": None,
            "code": None,
            "rgb": None,
        }

        self.rgb_pattern = r"\(?(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})\)?"

        self.select: Optional[SetupCustomColorView.ColorSelect] = None
        if palette:
            self.select = self.ColorSelect(palette, row=0)
            self.items.append(self.select)
        self.items.append(self.EditButton(row=1))
        self.palette = palette

        self.description_embed_field = {
            "name": "Custom Color",
            "value": "A custom color that will be exclusive to your server. "
            "This can be selected from previous years or created from scratch.",
        }

    def to_embed(self):
        embed = self.base_embed(user=self.interaction.user, title="Select Custom Color")

        embed.description = (
            "Please select a custom color that will be exclusive to your server! "
            "Either pick a color that you have used previous years, or create a new one. \n"
            "**This can only be set once, and cannot be edited! Make sure you're happy with it before confirming.**"
        )

        check = self.check_create_color()

        embed.add_field(
            name="Name",
            value=(
                self.color.name
                if self.color
                else (
                    (
                        self.create_color["name"]
                        if check["name"]
                        else f"Please provide a name for the color."
                    )
                    if self.create
                    else "None"
                )
            ),
        )

        embed.add_field(
            name="Code",
            value=(
                self.color.code
                if self.color
                else (
                    (
                        self.create_color["code"]
                        if check["code"]
                        else f"{self.create_color['code']} is not a valid code. The code must be 4 letters."
                    )
                    if self.create
                    else "None"
                )
            ),
        )

        embed.add_field(
            name="RGB",
            value=(
                self.color.rgb
                if self.color
                else (
                    (
                        self.create_color["rgb"]
                        if check["rgb"]
                        else f"{self.create_color['rgb']} is not a valid RGB value. "
                        f"The RGB must be in the format `r,g,b`."
                    )
                    if self.create
                    else "None"
                )
            ),
        )

        return embed

    def result_embed_field(self) -> dict[str, str]:
        return {
            "name": "Custom Color",
            "value": (
                (
                    f"{self.color.name} `{self.color.code}` {self.color.rgb}"
                    if not self.create
                    else f"Create new: "
                    f"{self.create_color['name']} `{self.create_color['code']}` ({self.create_color['rgb']})"
                )
                if self.complete
                else "Skipped"
            ),
        }

    def check(self) -> bool:
        if self.create:
            r, g, b = self.str_to_rgb()
            if (r, g, b) in self.palette:
                self.create = False
                self.color = self.palette[(r, g, b)]
                self.create_color = {
                    "name": self.color.name,
                    "code": self.color.code,
                    "rgb": str(self.color.rgb).replace(" ", ""),
                }

        self.complete = (
            self.color is not None
            if not self.create
            else all(self.check_create_color().values())
        )

        if self.select:
            if not self.create and self.color:
                self.select.set_options_default(self.color)
            else:
                self.select.set_options_default(None)

        return self.complete

    def check_create_color(self):
        r, g, b = self.str_to_rgb()

        return {
            "name": self.create_color["name"] is not None,
            "code": self.create_color["code"] is not None
            and len(self.create_color["code"]) == 4
            and self.create_color["code"].isalpha(),
            "rgb": self.create_color["rgb"] is not None
            and all(rgb is not None and 0 <= rgb <= 255 for rgb in [r, g, b]),
        }

    def str_to_rgb(self):
        if self.create_color["rgb"] and re.match(
            self.rgb_pattern, self.create_color["rgb"]
        ):
            r, g, b = map(
                int, re.match(self.rgb_pattern, self.create_color["rgb"]).groups()
            )
            self.create_color["rgb"] = f"{r},{g},{b}"
        else:
            r, g, b = None, None, None
        return r, g, b

    class EditButton(Button):
        def __init__(self, **kwargs):
            super().__init__(label="Create New Custom Color", **kwargs)

        @property
        def name(self):
            return (
                self.view.create_color["name"].strip()
                if self.view.create_color["name"] is not None
                else None
            )

        @property
        def code(self):
            return (
                self.view.create_color["code"].strip()
                if self.view.create_color["code"] is not None
                else None
            )

        @property
        def rgb(self):
            return (
                self.view.create_color["rgb"].strip()
                if self.view.create_color["rgb"] is not None
                else None
            )

        async def callback(self, interaction: Interaction):
            modal = EditModal(
                interaction.user.id,
                inputs={
                    "name": TextInput(
                        label="Name",
                        custom_id="name",
                        required=True,
                        default=self.name or None,
                    ),
                    "code": TextInput(
                        label="Code (4 letters)",
                        custom_id="code",
                        required=True,
                        min_length=4,
                        max_length=4,
                        default=self.code or None,
                    ),
                    "rgb": TextInput(
                        label="RGB (r,g,b)",
                        custom_id="rgb",
                        required=True,
                        min_length=5,
                        max_length=11,
                        default=self.rgb or None,
                        placeholder="r,g,b",
                    ),
                },
                title="Custom Color",
                custom_id="edit",
            )
            await interaction.response.send_modal(modal)
            await modal.wait()

            self.view.interaction = modal.interaction

            self.view.create_color["name"] = modal["name"]
            self.view.create_color["code"] = modal["code"].lower()
            self.view.create_color["rgb"] = modal["rgb"]

            self.view.create = True
            self.view.color = None

            self.view.check_create_color()

            await self.view.update_message()

    class ColorSelect(Select):
        def __init__(self, colors: Palette, **kwargs):
            self.colors = colors
            self.options_dict = {
                color.id: SelectOption(
                    label=color.name,
                    value=str(color.id),
                    emoji=color.emoji_formatted,
                )
                for color in colors
            }
            super().__init__(
                placeholder="Select a previous color",
                options=list(self.options_dict.values()),
                min_values=1,
                max_values=1,
                **kwargs,
            )

        async def callback(self, interaction: Interaction):
            self.view.interaction = interaction

            color: Color = next(
                (color for color in self.colors if color.id == int(self.values[0])),
                None,
            )
            self.view.color = color

            self.view.create = False

            self.view.create_color = {
                "name": color.name,
                "code": color.code,
                "rgb": str(color.rgb),
            }

            await self.view.update_message()

        def set_options_default(self, color: Optional[Color]):
            for option in self.options:
                option.default = False
            if color:
                self.options_dict[color.id].default = True
