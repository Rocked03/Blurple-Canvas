from objects.color import Color
from objects.discordObject import DiscordObject
from objects.event import Event
from objects.frame import Frame
from objects.pixel import Pixel
from objects.user import User
from postgresql.postgresql_manager import SQLManager


class Canvas(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        name: str = None,
        locked: bool = None,
        event_id: int = None,
        width: int = None,
        height: int = None,
        event: Event = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.locked = locked
        self.event_id = event_id
        self.width = width
        self.height = height

        self.event = Event(_id=event_id, **kwargs) if not event and event_id else event

    def is_locked(self):
        return self.locked

    def get_dimensions(self):
        return self.width, self.height

    async def place_pixel(
        self,
        sql_manager: SQLManager,
        *,
        user: User,
        guild_id: int = None,
        x: int,
        y: int,
        color: Color,
    ):
        pixel = Pixel(x=x, y=y, color=color, canvas=self)
        await sql_manager.update_pixel(pixel=pixel, user_id=user.id, guild_id=guild_id)

    async def get_frame(self, sql_manager: SQLManager, bbox: tuple[int, int, int, int]):
        frame = Frame(
            canvas_id=self.id,
            bbox=bbox,
        )
        await frame.load_pixels(sql_manager)
        return frame

    def __str__(self):
        return f"Canvas {self.name} ({self.id})"
