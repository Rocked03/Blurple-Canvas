from datetime import datetime

from objects.discordObject import DiscordObject
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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.user_id = user_id
        self.timestamp = timestamp

        self.user = User(_id=user_id, **kwargs) if user_id else None
        self.pixel = Pixel(canvas_id=canvas_id, x=x, y=y, color_id=color_id, **kwargs)

    def __str__(self):
        return f"HistoryRecord {self.user_id} {self.pixel} ({self.timestamp})"
