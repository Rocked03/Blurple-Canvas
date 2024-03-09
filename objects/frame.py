# Frame ( ID*, canvasID, guildID, xyxy, name )


from objects.canvas import Canvas
from objects.discordObject import DiscordObject
from objects.pixel import Pixel
from postgresql.postgresql_manager import SQLManager


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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.bbox: tuple[int, int, int, int] | None = (
            (x_0, x_1, y_0, y_1) if not bbox and (x_0 and x_1 and y_0 and y_1) else bbox
        )
        self.pixels = pixels

        self.canvas = (
            Canvas(_id=canvas_id, **kwargs) if not canvas and canvas_id else canvas
        )

    def bbox_formatted(self):
        return f"({self.bbox[0]}, {self.bbox[2]}) - ({self.bbox[1]}, {self.bbox[3]})"

    async def load_pixels(self, sql_manager: SQLManager):
        self.pixels = await sql_manager.fetch_pixels(self.canvas.id, self.bbox)

    def justified_pixels(self):
        if self.pixels is None:
            return []
        return [
            Pixel(
                x=pixel.x - self.bbox[0],
                y=pixel.y - self.bbox[2],
                color_id=pixel.color.id,
            )
            for pixel in self.pixels
            if self.bbox[0] <= pixel.x <= self.bbox[1]
            and self.bbox[2] <= pixel.y <= self.bbox[3]
        ]

    def __str__(self):
        return f"Frame {self.bbox_formatted()} ({self.canvas})"
