from __future__ import annotations

from typing import TYPE_CHECKING, Type, Callable

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageDraw2 import Font
from PIL.ImageFont import FreeTypeFont

from objects.coordinates import Coordinates

if TYPE_CHECKING:
    from objects.color import Color
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

    @property
    def adjusted_size(self) -> Coordinates:
        return self.frame.size * self.zoom

    def get_color(
        self, color: Color, replace_color: dict[int, tuple[int, int, int, int]] = None
    ) -> tuple[int, int, int, int]:
        if replace_color and color.id in replace_color:
            return replace_color[color.id]
        else:
            return color.rgba

    def frame_to_image_base(
        self, replace_color: dict[int, tuple[int, int, int, int]] = None
    ) -> Image.Image:
        img = Image.new("RGBA", self.frame.multiply_zoom(self.zoom), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for coordinates, pixel in self.frame.justified_pixels.items():
            coordinates *= self.zoom
            opposite_corner = coordinates + self.zoom
            draw.rectangle(
                (coordinates.to_tuple(), opposite_corner.to_tuple()),
                self.get_color(pixel.color, replace_color),
            )
        return img

    def generate_image(self) -> Image.Image:
        return self.frame_to_image_base()


class Config:
    def __init__(self, *args, **kwargs):
        self.font_path = None

    def get_font(self, size: int) -> FreeTypeFont:
        return ImageFont.truetype(self.font_path, size)

    def calculate_font_size(self, size: int, size_percent: float) -> int:
        return round(size * size_percent)


class DefaultStyle(Style):
    name = "Default"

    class Config(Config):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = DefaultStyle.Config()

    def generate_image(self) -> Image.Image:
        image = self.frame_to_image_base()

        # additional stuff here

        return image


class ClassicStyle(Style):
    name = "Classic"

    class Config(Config):
        def __init__(
            self,
            *args,
            font_path: str = "resources/fonts/GintoNordBlack.otf",
            font_size_title: int = 19,
            font_size_subtitle: int = 16,
            font_size_xy: int = 60,
            background_color: tuple[int, int, int, int] = (88, 101, 242, 255),
            border_width: int = 100,
            font_color_title: tuple[int, int, int, int] = (255, 255, 255, 255),
            font_color_subtitle: tuple[int, int, int, int] = (185, 196, 237, 255),
            font_color_xy: tuple[int, int, int, int] = (185, 196, 237, 255),
            subtitle_spacing: int = 30,
            blank_color: tuple[int, int, int, int] = None,
            **kwargs,
        ):
            super().__init__(*args, **kwargs)
            self.font_path = font_path

            self.font_size_title = self.get_font(font_size_title)
            self.font_size_subtitle = self.get_font(font_size_subtitle)
            self.font_size_xy = self.get_font(font_size_xy)

            self.background_color = background_color
            self.border_width = border_width

            self.font_color_title = font_color_title
            self.font_color_subtitle = font_color_subtitle
            self.font_color_xy = font_color_xy

            self.subtitle_spacing = subtitle_spacing
            self.blank_color = blank_color

    def __init__(self, config: Config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = config
        self.base: Image.Image = None
        self.draw: ImageDraw.ImageDraw = None

    @property
    def size(self) -> Coordinates:
        return self.adjusted_size + self.config.border_width

    @property
    def width(self) -> int:
        return self.size.x

    @property
    def height(self) -> int:
        return self.size.y

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
    ):
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

    def generate_image(self) -> Image.Image:
        image = self.frame_to_image_base(
            {1: self.config.blank_color} if self.config.blank_color else None
        )

        base = Image.new(
            "RGBA",
            self.size.to_tuple(),
            self.config.background_color,
        )
        draw = ImageDraw.Draw(base)
        self.base = base
        self.draw = draw

        base.paste(
            image,
            Coordinates.double(self.config.border_width).to_tuple(),
        )

        self.add_text(
            "Project",
            self.config.font_size_subtitle,
            lambda text_size: (
                (self.config.border_width - text_size.x) // 2,
                (
                    self.config.border_width // 2
                    - text_size.y
                    - self.config.subtitle_spacing // 2
                ),
            ),
            self.config.font_color_subtitle,
        )
        self.add_text(
            "Blurple",
            self.config.font_size_subtitle,
            lambda text_size: (
                (self.config.border_width - text_size.x) // 2,
                (self.config.border_width // 2 + self.config.subtitle_spacing // 2),
            ),
            self.config.font_color_subtitle,
        )

        self.add_text(
            (
                self.frame.name
                if self.frame.name
                else (
                    str(self.frame.focus)
                    if self.frame.focus
                    else self.frame.canvas.name
                )
            ),
            self.config.font_size_title,
            lambda text_size: (
                max((self.config.border_width - text_size.x) // 2, 3),
                (self.config.border_width - text_size.y) // 2,
            ),
            self.config.font_color_title,
        )

        if self.frame.focus:
            self.add_text(
                f"{self.frame.focus.x}  =  x",
                self.config.font_size_xy,
                lambda text_size: (
                    (
                        self.width
                        - text_size.x
                        - (self.config.border_width - text_size.y) // 2
                    ),
                    (self.config.border_width - text_size.y) // 2,
                ),
                self.config.font_color_xy,
            )

            self.add_text(
                f"y  =  {self.frame.focus.y}",
                self.config.font_size_xy,
                lambda text_size: (
                    (self.config.border_width - text_size.x) // 2,
                    (
                        self.height
                        - text_size.y
                        - (self.config.border_width - text_size.x) // 2
                    ),
                ),
                self.config.font_color_xy,
                rotation=90,
            )

        return base


class ClassicStyleNew(ClassicStyle):
    name = "Classic (New Blurple)"

    def __init__(self, *args, **kwargs):
        config = ClassicStyle.Config()

        super().__init__(config, *args, **kwargs)


class ClassicStyleLegacy(ClassicStyle):
    name = "Classic (Legacy Blurple)"

    def __init__(self, *args, **kwargs):
        config = ClassicStyle.Config(
            font_path="resources/fonts/UniSansHeavy.otf",
            font_size_subtitle=18,
            font_size_title=21,
            background_color=(114, 137, 218, 255),
            blank_color=(114, 137, 218, 127),
        )

        super().__init__(config, *args, **kwargs)


class Styles:
    STYLES: dict[int, Type[Style]] = {
        0: Style,  # Base style
        1: DefaultStyle,  # Default (need a better name)
        2: ClassicStyleNew,  # Classic style - New blurple
        3: ClassicStyleLegacy,  # Classic style - Legacy blurple
    }

    DEFAULT_STYLE = STYLES[1]

    @staticmethod
    def get_style(style_id: int) -> Type[Style]:
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
