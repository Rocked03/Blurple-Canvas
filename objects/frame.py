from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

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
        bbox: tuple[int, int, int, int] = None,
        canvas: Canvas = None,
        focus: tuple[int, int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.bbox: tuple[int, int, int, int] | None = (
            (x_0, x_1, y_0, y_1) if not bbox and (x_0 and x_1 and y_0 and y_1) else bbox
        )
        self.pixels = pixels
        self.focus = focus

        self.size = (self.bbox[2] - self.bbox[0] + 1, self.bbox[3] - self.bbox[1] + 1)

        from objects.canvas import Canvas

        self.canvas = (
            Canvas(_id=canvas_id, **kwargs)
            if canvas is None and canvas_id is not None
            else canvas
        )

    @staticmethod
    def from_coordinate(canvas: Canvas, xy: tuple[int, int], zoom: int):
        (x, y) = xy
        return Frame(
            canvas=canvas,
            bbox=(
                min(max(x - (zoom // 2), 0), canvas.width - zoom),
                min(max(y - (zoom // 2), 0), canvas.height - zoom),
                max(min(x + (zoom // 2), canvas.width), zoom),
                max(min(y + (zoom // 2), canvas.height), zoom),
            ),
            highlight=xy,
        )

    def bbox_formatted(self):
        return f"({self.bbox[0]}, {self.bbox[1]}) - ({self.bbox[2]}, {self.bbox[3]})"

    async def load_pixels(self, sql_manager: SQLManager):
        self.pixels = await sql_manager.fetch_pixels(self.canvas.id, self.bbox)

    def justified_pixels(self) -> dict[tuple[int, int], Pixel]:
        if self.pixels is None:
            return {}
        return {
            (pixel.x - self.bbox[0], pixel.y - self.bbox[1]): pixel
            for pixel in self.pixels
            if self.bbox[0] <= pixel.x <= self.bbox[2]
            and self.bbox[1] <= pixel.y <= self.bbox[3]
        }

    def justified_focus(self) -> tuple[int, int] | None:
        if self.focus is None:
            return None
        return self.focus[0] - self.bbox[0], self.focus[1] - self.bbox[1]

    def generate_image(self, *, zoom: int = 1) -> Image.Image:
        img = Image.new("RGBA", self.multiply_zoom(zoom), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for coordinates, pixel in self.justified_pixels().items():
            adjusted_coordinates = (coordinates[0] * zoom, coordinates[1] * zoom)
            opposite_corner = (
                adjusted_coordinates[0] + zoom,
                adjusted_coordinates[1] + zoom,
            )
            draw.rectangle(
                (adjusted_coordinates, opposite_corner),
                pixel.color.rgba,
            )
        return img

    def multiply_zoom(self, zoom: int) -> tuple[int, int]:
        return tuple[int, int]([self.size[0] * zoom, self.size[1] * zoom])

    def __str__(self):
        return f"Frame {self.bbox_formatted()} ({self.canvas})"


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
