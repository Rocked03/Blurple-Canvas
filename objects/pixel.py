from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from objects.coordinates import Coordinates
from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.canvas import Canvas
    from objects.color import Color


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
        xy: Coordinates = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.xy = xy if xy else Coordinates(x, y)
        self.x, self.y = self.xy.x, self.xy.y

        from objects.color import Color
        from objects.canvas import Canvas

        self.canvas: Optional[Canvas] = (
            Canvas(_id=canvas_id, **kwargs)
            if canvas is None and canvas_id is not None
            else canvas
        )
        self.color: Optional[Color] = (
            Color(_id=color_id, **kwargs)
            if color is None and color_id is not None
            else color
        )

    def get_coordinates(self):
        return self.x, self.y

    def __str__(self):
        return str(self.xy)