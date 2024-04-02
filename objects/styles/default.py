from __future__ import annotations

from PIL import Image, ImageDraw
from PIL.ImageFont import FreeTypeFont

from objects.coordinates import Coordinates
from objects.imager import Imager
from objects.style import Style, Config


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


class DefaultStyleLight(DefaultStyle):
    name = "Canvas Light (Default)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = DefaultStyle.Config()


class DefaultStyleDark(DefaultStyle):
    name = "Canvas Dark"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = DefaultStyle.Config(
            background_color=(35, 39, 42, 255),
            font_color_title=(255, 255, 255, 255),
            font_color_subtitle=(88, 101, 242, 255),
            icon_path="resources/icon_dark.png",
        )
