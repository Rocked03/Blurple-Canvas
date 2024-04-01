from __future__ import annotations

from typing import TYPE_CHECKING, Type, Callable

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageDraw2 import Font
from PIL.ImageFont import FreeTypeFont

from objects.coordinates import Coordinates
from objects.imager import Imager

if TYPE_CHECKING:
    from objects.color import Color
    from objects.frame import Frame


class Style:
    name = "Raw"

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

    def get_color(self, color: Color) -> tuple[int, int, int, int]:
        return color.rgba

    def frame_to_image_base(self) -> Image.Image:
        img = Image.new("RGBA", self.frame.multiply_zoom(self.zoom), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for coordinates, pixel in self.frame.justified_pixels.items():
            coordinates *= self.zoom
            opposite_corner = coordinates + self.zoom
            draw.rectangle(
                (coordinates.to_tuple(), opposite_corner.to_tuple()),
                self.get_color(pixel.color),
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


class Config:
    def __init__(self, *args, **kwargs):
        self.font_path = None

    def get_font(self, size: int) -> FreeTypeFont:
        return ImageFont.truetype(self.font_path, size)


class DefaultStyle(Style):
    name = "Default"

    class Config(Config):
        def __init__(
            self,
            *args,
            background_color: tuple[int, int, int, int] = (88, 101, 242, 255),
            min_width: int = 500,
            height_percent: float = 0.12,
            corner_radius_percent: float = 0.25,
            gap_size_percent: float = 0.03,
            font_path: str = "resources/fonts/GintoNordBlack.otf",
            font_size_title_percent: float = 0.4,
            font_size_subtitle_percent: float = 0.2,
            font_color_title: tuple[int, int, int, int] = (255, 255, 255, 255),
            font_color_subtitle: tuple[int, int, int, int] = (185, 196, 237, 255),
            icon_path: str = "resources/icon_light.png",
            icon_size_percent: float = 0.5,
            spacing_percent: float = 0.45,
            **kwargs,
        ):
            super().__init__(*args, **kwargs)
            self.background_color = background_color

            self.min_width = min_width
            self.height_percent = height_percent
            self.corner_radius_percent = corner_radius_percent
            self.gap_size_percent = gap_size_percent

            self.font_path = font_path
            self.font_size_title_percent = font_size_title_percent
            self.font_size_subtitle_percent = font_size_subtitle_percent

            self.font_color_title = font_color_title
            self.font_color_subtitle = font_color_subtitle

            self.icon_path = icon_path
            self.icon_size_percent = icon_size_percent

            self.spacing_percent = spacing_percent

            self.height: int = None
            self.gap_size: int = None

        def set_style(self, style: Style):
            self.height = round(style.adjusted_size.y * self.height_percent)
            self.gap_size = round(style.adjusted_size.y * self.gap_size_percent)

        @property
        def corner_radius(self) -> int:
            return round(self.height * self.corner_radius_percent)

        @property
        def font_title(self) -> FreeTypeFont:
            return self.get_font_from_percent(self.font_size_title_percent)

        @property
        def font_subtitle(self) -> FreeTypeFont:
            return self.get_font_from_percent(self.font_size_subtitle_percent)

        @property
        def icon_size(self) -> int:
            return round(self.height * self.icon_size_percent)

        @property
        def spacing(self):
            return round(self.height * self.spacing_percent)

        def get_font_from_percent(self, percent: float) -> FreeTypeFont:
            return self.get_font(round(self.height * percent))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = DefaultStyle.Config()

    def generate_image(self) -> Image.Image:
        self.config.set_style(self)

        image = self.frame_to_image_base()

        label_size = Coordinates(
            max(self.config.min_width, self.adjusted_size.x), self.config.height
        )

        label = Imager.round_rectangle(
            label_size.to_tuple(),
            self.config.corner_radius,
            self.config.background_color,
            all_corners=True,
        )
        draw = ImageDraw.Draw(label)
        self.base = label
        self.draw = draw

        self.add_text(
            self.frame.canvas.name,
            self.config.font_title,
            lambda text_size: ((label_size - text_size) // 2).to_tuple(),
            self.config.font_color_title,
        )

        self.add_text(
            "Project Blurple",
            self.config.font_subtitle,
            lambda text_size: (
                (label_size.x - text_size.x) // 2,
                (label_size.y - self.config.spacing) // 2 - text_size.y,
            ),
            self.config.font_color_subtitle,
        )

        self.add_text(
            (
                self.frame.name
                if self.frame.name
                else (str(self.frame.focus) if self.frame.focus else "Blurple Canvas")
            ),
            self.config.font_subtitle,
            lambda text_size: (
                (label_size.x - text_size.x) // 2,
                (label_size.y + self.config.spacing) // 2,
            ),
            self.config.font_color_subtitle,
        )

        if self.config.icon_size / label.width < 0.2:
            icon = Image.open(self.config.icon_path)
            icon = icon.resize((self.config.icon_size, self.config.icon_size))
            label.paste(
                icon,
                Coordinates(
                    (label_size.y - icon.height) // 2,
                    (label_size.y - icon.height) // 2,
                ).to_tuple(),
                icon,
            )

        # Combining it together

        base = Image.new(
            "RGBA",
            (
                max(self.adjusted_size.x, label_size.x),
                self.adjusted_size.y + label_size.y + self.config.gap_size,
            ),
        )
        base.paste(
            image,
            Coordinates(
                (base.width - image.width) // 2,
                0,
            ).to_tuple(),
        )
        base.paste(
            label,
            Coordinates(
                (base.width - label.width) // 2, image.height + self.config.gap_size
            ).to_tuple(),
        )

        return base


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

            self.font_title = self.get_font(font_size_title)
            self.font_subtitle = self.get_font(font_size_subtitle)
            self.font_xy = self.get_font(font_size_xy)

            self.background_color = background_color
            self.border_width = border_width

            self.font_color_title = font_color_title
            self.font_color_subtitle = font_color_subtitle
            self.font_color_xy = font_color_xy

            self.subtitle_spacing = subtitle_spacing

    def __init__(self, config: Config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = config

    @property
    def size(self) -> Coordinates:
        return self.adjusted_size + self.config.border_width

    @property
    def width(self) -> int:
        return self.size.x

    @property
    def height(self) -> int:
        return self.size.y

    def generate_image(self) -> Image.Image:
        image = self.frame_to_image_base()

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
            self.config.font_subtitle,
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
            self.config.font_subtitle,
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
            self.config.font_title,
            lambda text_size: (
                max((self.config.border_width - text_size.x) // 2, 3),
                (self.config.border_width - text_size.y) // 2,
            ),
            self.config.font_color_title,
        )

        if self.frame.focus:
            self.add_text(
                f"{self.frame.focus.x}  =  x",
                self.config.font_xy,
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
                self.config.font_xy,
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

    def get_color(self, color: Color) -> tuple[int, int, int, int]:
        if color.code == "blank":
            return 114, 137, 218, 127
        return color.rgba

    def __init__(self, *args, **kwargs):
        config = ClassicStyle.Config(
            font_path="resources/fonts/UniSansHeavy.otf",
            font_size_subtitle=18,
            font_size_title=21,
            background_color=(114, 137, 218, 255),
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
