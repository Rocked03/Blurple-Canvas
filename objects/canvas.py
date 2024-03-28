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
    from sql.sqlManager import SQLManager
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
        start_coordinates: list[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.locked = locked
        self.width = width
        self.height = height
        self.pixels = pixels
        self.cooldown_length = cooldown_length
        self.is_cache = is_cache

        self.start_coordinates: Coordinates = (
            Coordinates(start_coordinates[0], start_coordinates[1])
            if start_coordinates and len(start_coordinates) >= 2
            else Coordinates(1, 1)
        )

        self.bbox: Optional[BoundingBox] = (
            BoundingBox(Coordinates(width - 1, height - 1))
            if width and height
            else None
        )

        from objects.event import Event

        self.event = (
            Event(_id=event_id, **kwargs)
            if event is None and event_id is not None
            else event
        )

    @property
    def is_locked(self) -> bool:
        return self.locked

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.width, self.height

    @property
    def name_safe(self):
        return "".join([c for c in self.name.replace(" ", "_") if re.match(r"\w", c)])

    async def place_pixel(
        self,
        sql_manager: SQLManager,
        *,
        user: User,
        guild_id: int = None,
        xy: Coordinates,
        color: Color,
    ):
        from objects.pixel import Pixel

        pixel = Pixel(xy=xy, color=color, canvas=self)
        if self.pixels:
            self.pixels[xy] = pixel
        await sql_manager.update_pixel(pixel=pixel, user_id=user.id, guild_id=guild_id)

    async def place_pixels(
        self,
        sql_manager: SQLManager,
        *,
        user_id: int,
        guild_id: int = None,
        pixels: list[Pixel],
    ):
        for pixel in pixels:
            if pixel.canvas is None:
                pixel.canvas = self
            if self.pixels:
                self.pixels[pixel.xy] = pixel

        await sql_manager.update_pixels(
            pixels=pixels, user_id=user_id, guild_id=guild_id
        )

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
        await self.load_frame_pixels(sql_manager, frame)
        return frame

    async def regenerate_frame(self, sql_manager: SQLManager, frame: Frame) -> Frame:
        frame = frame.regenerate(self)
        await self.load_frame_pixels(sql_manager, frame)
        return frame

    async def load_frame_pixels(self, sql_manager: SQLManager, frame: Frame):
        if self.is_cache:
            frame.load_pixels_from_local(self)
        else:
            await frame.load_pixels(sql_manager)

    async def get_frame_full(self, sql_manager: SQLManager) -> Frame:
        return await self.get_frame(
            sql_manager,
            self.bbox,
        )

    async def get_frame_from_coordinate(
        self,
        sql_manager: SQLManager,
        xy: Coordinates,
        zoom: int,
        *,
        focus: bool = False,
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

    def get_true_coordinates(self, x: int, y: int) -> Coordinates:
        return Coordinates(x, y) - self.start_coordinates

    def get_f_coordinates(self, xy: Coordinates) -> Coordinates:
        return xy + self.start_coordinates

    async def edit(self, sql_manager: SQLManager):
        await sql_manager.update_canvas(self)

    def contains_adjusted_bbox(self, bbox: BoundingBox):
        return (bbox - self.start_coordinates) in self.bbox

    def bbox_percentage(self, bbox: BoundingBox):
        return bbox.area / self.bbox.area

    def __str__(self):
        return f"Canvas {self.name} ({self.id})"

    def __contains__(self, item):
        from objects.pixel import Pixel

        if isinstance(item, Coordinates):
            return item in self.bbox
        elif isinstance(item, BoundingBox):
            return item in self.bbox
        if isinstance(item, Pixel):
            return item.xy in self
        return False

    def __eq__(self, other):
        return self.id == other.id if isinstance(other, Canvas) else False
