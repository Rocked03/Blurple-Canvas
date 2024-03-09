from objects.canvas import Canvas
from objects.color import Color
from objects.discordObject import DiscordObject


class Pixel(DiscordObject):
    def __init__(
        self,
        *,
        canvas_id: int = None,
        x: int = None,
        y: int = None,
        color_id: int = None,
        color: Color = None,
        canvas: Canvas = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.x = x
        self.y = y

        self.canvas = (
            Canvas(_id=canvas_id, **kwargs) if not canvas and canvas_id else canvas
        )
        self.color = Color(_id=color_id, **kwargs) if not color and color_id else color

    def get_coordinates(self):
        return self.x, self.y

    def __str__(self):
        return f"({self.x}, {self.y})"
