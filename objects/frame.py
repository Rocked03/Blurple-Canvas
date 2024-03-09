# Frame ( ID*, canvasID, guildID, xyxy, name )


from objects.canvas import Canvas
from objects.discordObject import DiscordObject
from objects.guild import Guild
from objects.pixel import Pixel
from postgresql.postgresql_manager import SQLManager


class Frame(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        canvas_id: int = None,
        guild_id: int = None,
        x_0: int = None,
        y_0: int = None,
        x_1: int = None,
        y_1: int = None,
        name: str = None,
        pixels: list[Pixel] = None,
        canvas: Canvas = None,
        guild: Guild = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.bbox: tuple[int, int, int, int] | None = (
            (x_0, x_1, y_0, y_1) if x_0 and x_1 and y_0 and y_1 else None
        )
        self.pixels = pixels

        self.canvas = (
            Canvas(_id=canvas_id, **kwargs) if not canvas and canvas_id else canvas
        )
        self.guild = Guild(_id=guild_id, **kwargs) if not guild and guild_id else guild

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
        return f"Frame {self.name} ({self.id})"
