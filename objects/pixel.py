from objects.canvas import Canvas
from objects.color import Color
from objects.discordObject import DiscordObject


class Pixel(DiscordObject):
    def __init__(
        self,
        canvasId: int = None,
        x: int = None,
        y: int = None,
        colorId: int = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.canvas_id = canvasId
        self.x = x
        self.y = y
        self.color_id = colorId

        self.canvas = Canvas(_id=canvasId, **kwargs) if canvasId else None
        self.color = Color(_id=colorId, **kwargs) if colorId else None

    def get_coordinates(self):
        return self.x, self.y
