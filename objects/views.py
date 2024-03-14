from __future__ import annotations

from enum import Enum
from typing import Optional

from discord import Interaction, ButtonStyle, SelectOption
from discord.ui import View, Button, Select

from objects.color import Palette
from objects.coordinates import Coordinates


class ConfirmEnum(Enum):
    CONFIRM = "confirm"
    CANCEL = "cancel"


class NavigationEnum(Enum):
    LEFT = Coordinates(-1, 0)
    RIGHT = Coordinates(1, 0)
    UP = Coordinates(0, -1)
    DOWN = Coordinates(0, 1)


class ConfirmView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=30)
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

    async def defer(self):
        await self.interaction.response.defer()

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id


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
