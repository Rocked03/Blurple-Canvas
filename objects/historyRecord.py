from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.guild import Guild
    from objects.pixel import Pixel
    from objects.user import User


class HistoryRecord(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        canvas_id: int = None,
        user_id: int = None,
        x: int = None,
        y: int = None,
        color_id: int = None,
        timestamp: datetime = None,
        guild_id: int = None,
        user: User = None,
        pixel: Pixel = None,
        guild: Guild = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.timestamp = timestamp

        from objects.user import User
        from objects.pixel import Pixel
        from objects.guild import Guild

        self.user = (
            User(_id=user_id, **kwargs)
            if user is None and user_id is not None
            else user
        )
        self.pixel = (
            Pixel(canvas_id=canvas_id, x=x, y=y, color_id=color_id, **kwargs)
            if pixel is None
            else pixel
        )
        self.guild = (
            Guild(_id=guild_id, **kwargs)
            if guild is None and guild_id is not None
            else guild
        )

    def __str__(self):
        return f"HistoryRecord {self.user.id} {self.pixel} ({self.timestamp})"
