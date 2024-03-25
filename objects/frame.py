from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, Optional

from PIL import Image, ImageDraw

from objects.color import Color
from objects.coordinates import BoundingBox, Coordinates
from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.user import User
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
                    min(max(x - (zoom // 2), 0), canvas.width - zoom),
                    min(max(y - (zoom // 2), 0), canvas.height - zoom),
                ),
                Coordinates(
                    max(min(x + (zoom // 2), canvas.width - 1), zoom - 1),
                    max(min(y + (zoom // 2), canvas.height - 1), zoom - 1),
                ),
            ),
            focus=xy if focus else None,
        )

    @property
    def centroid(self) -> Coordinates:
        return Coordinates(
            (self.bbox.x0 + self.bbox.x1) // 2, (self.bbox.y0 + self.bbox.y1) // 2
        )

    async def load_pixels(self, sql_manager: SQLManager):
        self.pixels = await sql_manager.fetch_pixels(self.canvas.id, self.bbox)

    def load_pixels_from_local(self, canvas: Canvas):
        pixels = canvas.pixels
        self.pixels = [pixel for pixel in pixels.values() if pixel in self.bbox]

    def regenerate(self, canvas: Canvas):
        return Frame(canvas=canvas, bbox=self.bbox, focus=self.focus)

    @property
    def justified_pixels(self) -> dict[Coordinates, Pixel]:
        if self.pixels is None:
            return {}
        return {
            Coordinates(pixel.x - self.bbox.x0, pixel.y - self.bbox.y0): copy(pixel)
            for pixel in self.pixels
            if self.bbox.x0 <= pixel.x <= self.bbox.x1
            and self.bbox.y0 <= pixel.y <= self.bbox.y1
        }

    @property
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
        for coordinates, pixel in self.justified_pixels.items():
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
        pixels = self.justified_pixels
        emoji_list = []
        justified_focus = self.justified_focus if focus else None
        for y in range(self.bbox.height):
            emoji_list.append(
                "".join(
                    [
                        (
                            pixels.get(Coordinates(x, y)).color.emoji_formatted
                            if Coordinates(x, y) != justified_focus
                            else focus.emoji_formatted
                        )
                        for x in range(self.bbox.width)
                    ]
                )
            )
        if focus:
            txt = " • " + pixels.get(justified_focus).color.emoji_formatted
            if new_color:
                txt += " \u2192 " + new_color.emoji_formatted
            emoji_list[justified_focus.y] += txt
        return "\n".join(emoji_list)

    def multiply_zoom(self, zoom: int) -> tuple[int, int]:
        return tuple[int, int]([self.bbox.width * zoom, self.bbox.height * zoom])

    def __str__(self):
        return f"Frame {self.bbox} ({self.canvas})"


class CustomFrame(Frame):
    def __init__(
        self,
        *,
        is_guild_owned: bool,
        _id: str = None,
        canvas_id: int = None,
        owner_id: int = None,
        name: str = None,
        style_id: int = None,
        canvas: Canvas = None,
        owner: User | Guild = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.is_guild_owned = is_guild_owned
        self.style_id = style_id

        from objects.canvas import Canvas

        self.canvas = (
            Canvas(_id=canvas_id, **kwargs)
            if canvas is None and canvas_id is not None
            else canvas
        )

        if owner is not None:
            self.owner = owner
        elif is_guild_owned:
            from objects.guild import Guild

            self.owner: Guild = Guild(_id=owner_id, **kwargs)
        else:
            from objects.user import User

            self.owner: User = User(_id=owner_id, **kwargs)

    @property
    def owner_id(self):
        from objects.user import User
        from objects.guild import Guild

        if isinstance(self.owner, User):
            return self.owner.id
        elif isinstance(self.owner, Guild):
            return self.owner.guild_id

    async def delete(self, sql_manager: SQLManager):
        await sql_manager.delete_frame(self.id)

    def __str__(self):
        return f"Custom Frame {self.name} ({self.id}) ({self.canvas})"
