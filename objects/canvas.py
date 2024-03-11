from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from objects.coordinates import BoundingBox, Coordinates
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
        pixels: dict[Coordinates, Pixel] = None,
        cooldown_length: int = None,
        is_cache: bool = False,
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
        self.is_cache = is_cache

        self.bbox: Optional[BoundingBox] = (
            BoundingBox(Coordinates(1, 1), Coordinates(width, height))
            if width and height
            else None
        )

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
        pixel = Pixel(xy=Coordinates(x, y), color=color, canvas=self)
        await sql_manager.update_pixel(pixel=pixel, user_id=user.id, guild_id=guild_id)

    async def lock(self, sql_manager: SQLManager):
        self.locked = True
        await sql_manager.lock_canvas(self)

    async def unlock(self, sql_manager: SQLManager):
        self.locked = False
        await sql_manager.unlock_canvas(self)

    async def get_frame(
        self, sql_manager: SQLManager, bbox: BoundingBox, focus: Coordinates = None
    ) -> Frame:
        if bbox not in self.bbox:
            raise ValueError("Coordinates out of bounds")

        from objects.frame import Frame

        frame = Frame(
            canvas_id=self.id,
            bbox=bbox,
            focus=focus,
        )
        if self.is_cache:
            frame.load_pixels_from_local(self)
        else:
            await frame.load_pixels(sql_manager)
        return frame

    async def get_frame_full(self, sql_manager: SQLManager) -> Frame:
        return await self.get_frame(
            sql_manager,
            BoundingBox(Coordinates(1, 1), Coordinates(self.width, self.height)),
        )

    async def get_frame_from_coordinate(
        self,
        sql_manager: SQLManager,
        xy: Coordinates,
        zoom: int,
        focus: Coordinates = None,
    ) -> Frame:
        if zoom < 5:
            raise ValueError("Zoom must be at least 5")
        if zoom > self.width and zoom > self.height:
            zoom = max(self.width, self.height)

        from objects.frame import Frame

        frame = Frame.from_coordinate(self, xy, zoom, focus=focus)
        if self.is_cache:
            frame.load_pixels_from_local(self)
        else:
            await frame.load_pixels(sql_manager)
        return frame

    def name_safe(self):
        return "".join([c for c in self.name.replace(" ", "_") if re.match(r"\w", c)])

    def __str__(self):
        return f"Canvas {self.name} ({self.id})"

    def __contains__(self, item):
        if isinstance(item, Coordinates):
            return item in self.bbox
        if isinstance(item, Pixel):
            return item.xy in self
        return False
