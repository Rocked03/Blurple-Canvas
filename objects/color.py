from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.guild import Guild
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
        guild: Guild = None,
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

        from objects.guild import Guild
        from objects.event import Event

        self.guild = Guild(_id=guild_id, **kwargs) if guild_id else guild
        self.event = Event(_id=event_id, **kwargs) if event_id else event

    def emoji_formatted(self):
        return f"<:{self.emoji_name}:{self.emoji_id}>" if self.emoji_name else None

    def rgba_formatted(self):
        return f"rgba({', '.join(map(str, self.rgba))})" if self.rgba else None

    def __str__(self):
        return f"Color {self.name} {self.rgba_formatted()}"

    def __eq__(self, other):
        return self.id == other.id
