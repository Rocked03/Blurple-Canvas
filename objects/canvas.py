from __future__ import annotations

import re
from typing import TYPE_CHECKING

from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.color import Color
    from objects.event import Event
    from objects.frame import Frame
    from objects.pixel import Pixel
    from objects.sqlManager import SQLManager
    from objects.user import User


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
        pixels: dict[tuple[int, int], Pixel] = None,
        cooldown_length: int = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.locked = locked
        self.event_id = event_id
        self.width = width
        self.height = height
        self.pixels = pixels
        self.cooldown_length = cooldown_length

        from objects.event import Event

        self.event = (
            Event(_id=event_id, **kwargs)
            if event is None and event_id is not None
            else event
        )

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

    async def get_frame(
        self, sql_manager: SQLManager, bbox: tuple[int, int, int, int]
    ) -> Frame:
        if (
            bbox[0] <= 0
            or bbox[1] <= 0
            or bbox[2] > self.width
            or bbox[3] > self.height
        ):
            raise ValueError("Coordinates out of bounds")

        from objects.frame import Frame

        frame = Frame(
            canvas_id=self.id,
            bbox=bbox,
        )
        await frame.load_pixels(sql_manager)
        return frame

    async def get_frame_full(self, sql_manager: SQLManager) -> Frame:
        return await self.get_frame(sql_manager, (1, 1, self.width, self.height))

    async def get_frame_from_coordinate(
        self, sql_manager: SQLManager, xy: tuple[int, int], zoom: int
    ) -> Frame:
        from objects.frame import Frame

        frame = Frame.from_coordinate(self, xy, zoom)
        await frame.load_pixels(sql_manager)
        return frame

    def name_safe(self):
        return "".join([c for c in self.name if re.match(r"\w", c)])

    def __str__(self):
        return f"Canvas {self.name} ({self.id})"
