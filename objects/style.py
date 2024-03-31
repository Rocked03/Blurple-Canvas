from __future__ import annotations

from typing import TYPE_CHECKING, Type

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from objects.coordinates import Coordinates
    from objects.frame import Frame


class Style:
    name = "Raw"

    def __init__(
        self,
        frame: Frame,
        *,
        zoom: int = 1,
        max_size: Coordinates = None,
    ):
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

    @staticmethod
    def get_style(style_id: int) -> Type[Style]:
        if style_id is None or style_id not in STYLES:
            return DEFAULT_STYLE
        return STYLES[style_id]

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


class DefaultStyle(Style):
    name = "Default"

    class Config:
        def __init__(self):
            pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = DefaultStyle.Config()

    def generate_image(self) -> Image.Image:
        image = self.frame_to_image_base()

        # additional stuff here

        return image


class ClassicStyle(Style):
    name = "Classic"

    class Config:
        def __init__(self):
            pass

    def __init__(self, config: Config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = config

    def generate_image(self) -> Image.Image:
        image = self.frame_to_image_base()

        # additional stuff here

        return image


class ClassicStyleNew(ClassicStyle):
    name = "Classic (New Blurple)"

    def __init__(self, *args, **kwargs):
        config = ClassicStyle.Config()

        super().__init__(config, *args, **kwargs)


class ClassicStyleLegacy(ClassicStyle):
    name = "Classic (Legacy Blurple)"

    def __init__(self, *args, **kwargs):
        config = ClassicStyle.Config()

        super().__init__(config, *args, **kwargs)


STYLES: dict[int, Type[Style]] = {
    0: Style,  # Base style
    1: DefaultStyle,  # Default (need a better name)
    2: ClassicStyleNew,  # Classic style - New blurple
    3: ClassicStyleLegacy,  # Classic style - Legacy blurple
}

DEFAULT_STYLE = STYLES[1]
