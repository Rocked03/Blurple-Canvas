from __future__ import annotations

from typing import Iterable

from objects.color import Color


class Palette:
    def __init__(self, colors: Iterable[Color]):
        self.colors: dict[int, Color] = {color.id: color for color in colors}
        self.edit: Color = next(
            (color for color in self.colors.values() if color.code == "edit"), None
        )

    def get_all_colors(self) -> list[Color]:
        return [color for color in self.colors.values() if color != self.edit]

    def get_global_colors(self) -> list[Color]:
        return [color for color in self.colors.values() if color.is_global]

    def get_guild_colors(self, guild_id: int) -> list[Color]:
        return [
            color
            for color in self.colors.values()
            if color.guild and color.guild.id == guild_id
        ]

    def get_event_colors(self, event_id: int) -> list[Color]:
        return [
            color
            for color in self.colors.values()
            if color.event and color.event.id == event_id
        ]

    def get_available_colors(self, guild_id: int, event_id: int) -> list[Color]:
        return self.get_global_colors() + list(
            set(self.get_guild_colors(guild_id)) & set(self.get_event_colors(event_id))
        )

    def get_all_colors_as_palette(self) -> Palette:
        return Palette(self.get_all_colors())

    def get_available_colors_as_palette(self, guild_id: int, event_id: int) -> Palette:
        return Palette(
            self.get_available_colors(guild_id, event_id)
            + ([self.edit] if self.edit else [])
        )

    def get_edit_color(self) -> Color:
        return self.edit

    def sorted(self, colors: list[Color] = None) -> list[Color]:
        if colors is None:
            return sorted(self.get_all_colors())
        else:
            return sorted(colors)

    def sorted_separated(self, colors: list[Color] = None) -> list[Color]:
        return sorted(
            self.sorted(colors),
            key=lambda color: color.is_global,
        )

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.colors[item]
        elif isinstance(item, str):
            if item.isnumeric():
                return self.colors[int(item)]
            return next(
                (
                    color
                    for color in self.colors.values()
                    if color.name == item or color.code == item
                ),
                None,
            )
        elif isinstance(item, Color):
            return item
        elif item is None:
            return None
        else:
            raise ValueError(f"Invalid item {item}")

    def __contains__(self, item):
        if isinstance(item, Color):
            return item.id in self.colors
        elif isinstance(item, int):
            return item in self.colors
        elif isinstance(item, str):
            if item.isnumeric():
                return int(item) in self.colors
            return item in [color.name for color in self.colors.values()] or item in [
                color.code for color in self.colors.values()
            ]
        else:
            return False
