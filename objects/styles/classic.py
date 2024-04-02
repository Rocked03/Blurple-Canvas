from __future__ import annotations

from PIL import Image, ImageDraw

from objects.color import Color
from objects.coordinates import Coordinates
from objects.style import Style, Config


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
