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

    @property
    def coordinates(self) -> Coordinates:
        return self.xy

    @property
    def x(self) -> int:
        return self.xy.x

    @property
    def y(self) -> int:
        return self.xy.y

    def __str__(self):
        return str(self.xy)
