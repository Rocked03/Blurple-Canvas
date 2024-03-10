from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.x = x
        self.y = y

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
        return f"({self.x}, {self.y})"
