from __future__ import annotations

from copy import copy
from typing import TYPE_CHECKING, Type, Callable

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from objects.coordinates import Coordinates
from objects.pixel import Pixel

if TYPE_CHECKING:
    from objects.color import Color
    from objects.frame import Frame


class Style:
    name = "Raw"
    id = 0
    hide_embed_info: bool = False

    def __init__(
        self,
        frame: Frame,
        *,
        zoom: int = None,
        max_size: Coordinates = None,
    ):
        self.frame = frame

        self.base: Image.Image = None
        self.draw: ImageDraw.ImageDraw = None

        if max_size is None and zoom is None:
            max_size = Coordinates.double(
                3000
                if frame.bbox.max_dimension >= frame.canvas.bbox.max_dimension // 2
                else (
                    2000
                    if frame.bbox.max_dimension >= frame.canvas.bbox.max_dimension // 4
                    else 1500
                )
            )

        if zoom or max_size:
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
        else:
            self.zoom = 1

    @property
    def adjusted_size(self) -> Coordinates:
        return self.frame.size * self.zoom

    def get_color(self, pixel: Pixel) -> tuple[int, int, int, int]:
        return pixel.color.rgba

    def frame_to_image_base(self) -> Image.Image:
        img = Image.new("RGBA", self.frame.multiply_zoom(self.zoom), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for coordinates, pixel in self.frame.justified_pixels.items():
            coordinates *= self.zoom
            opposite_corner = coordinates + self.zoom
            draw.rectangle(
                (coordinates.to_tuple(), opposite_corner.to_tuple()),
                self.get_color(pixel),
            )
        return img

    def generate_image(self) -> Image.Image:
        return self.frame_to_image_base()

    def text_size(self, text: str, font: FreeTypeFont) -> Coordinates:
        return Coordinates(*self.draw.textbbox(text=text, xy=(0, 0), font=font)[2:])

    def add_text(
        self,
        text: str,
        font: FreeTypeFont,
        position: Callable[[Coordinates], tuple[int, int]],
        color: tuple[int, int, int, int],
        *,
        rotation: int = 0,
        max_width: int = None,
    ):
        text_size = self.text_size(text, font)
        if max_width and text_size.x > max_width:
            new_font = copy(font)
            new_font.size = max_width * font.size // text_size.x
            font = new_font
            text_size = self.text_size(text, font)

        if rotation == 0:
            self.draw.text(
                position(text_size),
                text,
                font=font,
                fill=color,
            )
        else:
            img = Image.new("RGBA", text_size.to_tuple())
            ImageDraw.Draw(img).text((0, 0), text, font=font, fill=color)
            img = img.rotate(rotation, expand=True)
            self.base.paste(
                img,
                position(Coordinates(*img.size)),
                img,
            )


class Config:
    def __init__(self, *args, **kwargs):
        self.font_path = None

    def get_font(self, size: int) -> FreeTypeFont:
        return ImageFont.truetype(self.font_path, size)


class Styles:
    from objects.styles.default import DefaultStyleLight, DefaultStyleDark
    from objects.styles.classic import ClassicStyleNew, ClassicStyleLegacy
    from objects.styles.filter import CrunchyStyle, HolographicStyle
    from objects.styles.template import WesternStyle, PhotographStyle, DifferenceStyle

    STYLES: dict[int, Type[Style]] = {
        # Base Styles (0-9)
        0: Style,  # Raw unedited
        1: DefaultStyleLight,  # Canvas Light (default)
        2: DefaultStyleDark,  # Canvas Dark
        3: ClassicStyleNew,  # Classic style - New blurple
        4: ClassicStyleLegacy,  # Classic style - Legacy blurple
        # Fun Designs (10-29)
        10: CrunchyStyle,  # Crunchy
        11: WesternStyle,  # Western (sepia)
        12: HolographicStyle,  # Holographic
        # Memes (30-49)
        30: PhotographStyle,  # Look at this photograaaaaph
        31: DifferenceStyle,  # Corporate needs you to find the difference
    }

    DEFAULT_STYLE = STYLES[1]

    @staticmethod
    def get_style(style_id: int = None) -> Type[Style]:
        if style_id is None or not Styles.contains(style_id):
            return Styles.DEFAULT_STYLE
        return Styles.STYLES[style_id]

    @staticmethod
    def get_styles() -> dict[int, Type[Style]]:
        return Styles.STYLES

    @staticmethod
    def get_names() -> list[str]:
        return [style.name for style in Styles.STYLES.values()]

    @staticmethod
    def contains(style_id: int) -> bool:
        return style_id in Styles.STYLES
