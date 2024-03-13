from __future__ import annotations

import colorsys
from typing import Optional, TYPE_CHECKING, Iterable

from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.guild import Participation
    from objects.event import Event


class Color(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        name: str = None,
        code: str = None,
        emoji_name: str = None,
        emoji_id: int = None,
        _global: bool = None,
        rgba: list[int] = None,
        guild_id: int = None,
        guild: Participation = None,
        event_id: int = None,
        event: Event = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.code = code
        self.emoji_name = emoji_name
        self.emoji_id = emoji_id
        self.is_global = _global

        self.rgba: Optional[tuple[int, int, int, int]] = (
            tuple(rgba[i] if len(rgba) > i else [0, 0, 0, 255][i] for i in range(4))
            if rgba
            else None
        )

        from objects.guild import Participation
        from objects.event import Event

        self.guild = Participation(_id=guild_id, **kwargs) if guild_id else guild
        self.event = Event(_id=event_id, **kwargs) if event_id else event

    def emoji_formatted(self):
        return f"<:{self.emoji_name}:{self.emoji_id}>" if self.emoji_name else None

    def rgba_formatted(self):
        return f"rgba({', '.join(map(str, self.rgba))})" if self.rgba else None

    def to_hsl(self):
        h, s, l = colorsys.rgb_to_hsv(*map(lambda c: c / 255.0, self.rgba[:3]))
        h = h if 0 < h else 1
        return h, s, l

    def is_valid(self, guild_id: int, event_id: int = None):
        return self.is_global or (
            self.guild.id == guild_id
            and (self.event.id == event_id or self.event.id is None or event_id is None)
        )

    def __str__(self):
        return f"Color {self.name} {self.rgba_formatted()}"

    def __eq__(self, other):
        if isinstance(other, Color):
            return self.id == other.id
        return False

    def __gt__(self, other):
        if isinstance(other, Color):
            return self.to_hsl() > other.to_hsl()
        raise TypeError

    def __lt__(self, other):
        if isinstance(other, Color):
            return self.to_hsl() < other.to_hsl()
        raise TypeError


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
