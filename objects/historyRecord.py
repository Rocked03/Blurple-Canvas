from datetime import datetime

from objects.discordObject import DiscordObject
from objects.pixel import Pixel
from objects.user import User


class HistoryRecord(DiscordObject):
    def __init__(
        self,
        canvasId: int = None,
        userId: int = None,
        x: int = None,
        y: int = None,
        colorId: int = None,
        timestamp: datetime = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.user_id = userId
        self.timestamp = timestamp

        self.user = User(_id=userId, **kwargs) if userId else None
        self.pixel = Pixel(canvasId=canvasId, x=x, y=y, colorId=colorId, **kwargs)
