from typing import Iterable

from objects.color import Color


class Palette:
    def __init__(self, colors: Iterable[Color]):
        self.colors: dict[int, Color] = {color.id: color for color in colors}
        self.edit: Color = next(
            (color for color in self.colors.values() if color.code == "edit"), None
        )

    def get_global_colors(self):
        return [color for color in self.colors.values() if color.is_global]

    def get_guild_colors(self, guild_id: int):
        return [
            color
            for color in self.colors.values()
            if color.guild and color.guild.id == guild_id
        ]

    def get_event_colors(self, event_id: int):
        return [
            color
            for color in self.colors.values()
            if color.event and color.event.id == event_id
        ]

    def get_available_colors(self, guild_id: int, event_id: int):
        return self.get_global_colors() + list(
            set(self.get_guild_colors(guild_id)) & set(self.get_event_colors(event_id))
        )

    def get_edit_color(self):
        return self.edit

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
