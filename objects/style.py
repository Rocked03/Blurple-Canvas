from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from objects.coordinates import Coordinates
    from objects.frame import Frame


class Style:
    def __init__(self, frame: Frame, *, zoom: int = 1, max_size: Coordinates = None):
        self.frame = frame

        self.zoom = (
            zoom
            if not max_size
            else max(
                1,
                min(
                    max_size.x // self.frame.bbox.width,
                    max_size.y // self.frame.bbox.height,
                ),
            )
        )

    def frame_to_image_base(self) -> Image.Image:
        img = Image.new("RGBA", self.frame.multiply_zoom(self.zoom), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for coordinates, pixel in self.frame.justified_pixels.items():
            coordinates *= self.zoom
            opposite_corner = coordinates + self.zoom
            draw.rectangle(
                (coordinates.to_tuple(), opposite_corner.to_tuple()),
                pixel.color.rgba,
            )
        return img

    def generate_image(self) -> Image.Image:
        return self.frame_to_image_base()
