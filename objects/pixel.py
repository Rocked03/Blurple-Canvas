from objects.canvas import Canvas
from objects.color import Color
from objects.discordObject import DiscordObject


class Pixel(DiscordObject):
    def __init__(
        self,
        canvas_id: int = None,
        x: int = None,
        y: int = None,
        color_id: int = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.canvas_id = canvas_id
        self.x = x
        self.y = y
        self.color_id = color_id

        self.canvas = Canvas(_id=canvas_id, **kwargs) if canvas_id else None
        self.color = Color(_id=color_id, **kwargs) if color_id else None

    def get_coordinates(self):
        return self.x, self.y

    def __str__(self):
        return f"({self.x}, {self.y})"
