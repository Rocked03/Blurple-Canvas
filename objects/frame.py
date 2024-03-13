from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, Optional

from PIL import Image, ImageDraw

from objects.color import Color
from objects.coordinates import BoundingBox, Coordinates
from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.canvas import Canvas
    from objects.guild import Guild
    from objects.pixel import Pixel
    from objects.sqlManager import SQLManager


class Frame(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        canvas_id: int = None,
        x_0: int = None,
        y_0: int = None,
        x_1: int = None,
        y_1: int = None,
        pixels: list[Pixel] = None,
        bbox: BoundingBox = None,
        canvas: Canvas = None,
        focus: Coordinates = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.bbox: Optional[BoundingBox] = (
            BoundingBox(Coordinates(x_0, y_0), Coordinates(x_1, y_1))
            if not bbox and (x_0 and y_0 and x_1 and y_1)
            else bbox
        )
        self.pixels = pixels
        self.focus = focus

        self.size = self.bbox.size

        from objects.canvas import Canvas

        self.canvas: Optional[Canvas] = (
            Canvas(_id=canvas_id, **kwargs)
            if canvas is None and canvas_id is not None
            else canvas
        )

    @staticmethod
    def from_coordinate(
        canvas: Canvas, xy: Coordinates, zoom: int, *, focus: bool = False
    ):
        (x, y) = xy.to_tuple()
        if zoom < 1:
            raise ValueError("Zoom must be at least 1")
        if xy not in canvas.bbox:
            raise ValueError("Coordinates out of bounds")
        return Frame(
            canvas=canvas,
            bbox=BoundingBox(
                Coordinates(
                    min(max(x - (zoom // 2), 1), canvas.width - zoom + 1),
                    min(max(y - (zoom // 2), 1), canvas.height - zoom + 1),
                ),
                Coordinates(
                    max(min(x + (zoom // 2), canvas.width), zoom),
                    max(min(y + (zoom // 2), canvas.height), zoom),
                ),
            ),
            focus=xy if focus else None,
        )

    async def load_pixels(self, sql_manager: SQLManager):
        self.pixels = await sql_manager.fetch_pixels(self.canvas.id, self.bbox)

    def load_pixels_from_local(self, canvas: Canvas):
        pixels = canvas.pixels
        self.pixels = [pixel for pixel in pixels.values() if pixel in self.bbox]

    def regenerate(self, canvas: Canvas):
        return Frame(canvas=canvas, bbox=self.bbox, focus=self.focus)

    def justified_pixels(self) -> dict[Coordinates, Pixel]:
        if self.pixels is None:
            return {}
        return {
            Coordinates(pixel.x - self.bbox.x0, pixel.y - self.bbox.y0): copy(pixel)
            for pixel in self.pixels
            if self.bbox.x0 <= pixel.x <= self.bbox.x1
            and self.bbox.y0 <= pixel.y <= self.bbox.y1
        }

    def justified_focus(self) -> Optional[Coordinates]:
        if self.focus is None:
            return None
        return Coordinates(self.focus.x - self.bbox.x0, self.focus.y - self.bbox.y0)

    def generate_image(
        self, *, zoom: int = 1, max_size: Coordinates = None
    ) -> Image.Image:
        if max_size:
            zoom = max(
                1,
                min(
                    max_size.x // self.bbox.width,
                    max_size.y // self.bbox.height,
                ),
            )
        img = Image.new("RGBA", self.multiply_zoom(zoom), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for coordinates, pixel in self.justified_pixels().items():
            if zoom != 1:
                adjusted_coordinates = (coordinates.x * zoom, coordinates.y * zoom)
            # elif max_size is not None:
            #     adjusted_coordinates = (
            #         coordinates.x * max_size.x // self.bbox.width,
            #         coordinates.y * max_size.y // self.bbox.height,
            #     )
            else:
                adjusted_coordinates = coordinates.to_tuple()
            opposite_corner = (
                adjusted_coordinates[0] + zoom,
                adjusted_coordinates[1] + zoom,
            )
            draw.rectangle(
                (adjusted_coordinates, opposite_corner),
                pixel.color.rgba,
            )
        return img

    def to_emoji(self, *, focus: Color = None, new_color: Color = None) -> str:
        pixels = self.justified_pixels()
        emoji_list = []
        justified_focus = self.justified_focus() if focus else None
        for y in range(self.bbox.height):
            emoji_list.append(
                "".join(
                    [
                        (
                            pixels.get(Coordinates(x, y)).color.emoji_formatted()
                            if Coordinates(x, y) != justified_focus
                            else focus.emoji_formatted()
                        )
                        for x in range(self.bbox.width)
                    ]
                )
            )
        if focus:
            txt = " • " + pixels.get(justified_focus).color.emoji_formatted()
            if new_color:
                txt += " \u2192 " + new_color.emoji_formatted()
            emoji_list[justified_focus.y] += txt
        return "\n".join(emoji_list)

    def multiply_zoom(self, zoom: int) -> tuple[int, int]:
        return tuple[int, int]([self.bbox.width * zoom, self.bbox.height * zoom])

    def __str__(self):
        return f"Frame {self.bbox} ({self.canvas})"


class CustomFrame(Frame):
    def __init__(
        self, *, name: str = None, guild_id: int = None, guild: Guild = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name

        from objects.guild import Guild

        self.guild = (
            Guild(_id=guild_id, **kwargs)
            if guild is None and guild_id is not None
            else guild
        )

    def __str__(self):
        return f"Custom Frame {self.name} ({self.id}) ({self.canvas})"
