from datetime import datetime

from objects.discordObject import DiscordObject
from objects.guild import Guild
from objects.pixel import Pixel
from objects.user import User


class HistoryRecord(DiscordObject):
    def __init__(
        self,
        _id: int = None,
        canvas_id: int = None,
        user_id: int = None,
        x: int = None,
        y: int = None,
        color_id: int = None,
        timestamp: datetime = None,
        guild_id: int = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.timestamp = timestamp

        self.user = User(_id=user_id, **kwargs) if user_id else None
        self.pixel = Pixel(canvas_id=canvas_id, x=x, y=y, color_id=color_id, **kwargs)
        self.guild = Guild(_id=guild_id, **kwargs) if guild_id else None

    def __str__(self):
        return f"HistoryRecord {self.user.id} {self.pixel} ({self.timestamp})"
