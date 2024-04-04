from enum import Enum
from random import choice

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

from objects.color import Color
from objects.coordinates import Coordinates
from objects.pixel import Pixel
from objects.style import Style, Config


class TemplateStyle(Style):
    class Config(Config):
        def __init__(
            self,
            *args,
            template_path: str,
            position: Coordinates,
            cutout_size: Coordinates = None,
            rotation: int = 0,
            background_color: tuple[int, int, int, int] = 0,
            **kwargs
        ):
            super().__init__(*args, **kwargs)

            self.template_path = template_path
            self.position = position
            self.cutout_size = cutout_size
            self.rotation = rotation
            self.background_color = background_color

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: TemplateStyle.Config = None

    class Size(Enum):
        FIT = 0
        FILL = 1

    def process_image(self, image: Image.Image, size: Size = Size.FIT) -> Image.Image:
        if self.config.cutout_size:
            image_size = Coordinates(*image.size)
            ratios = (
                self.config.cutout_size.x / image_size.x,
                self.config.cutout_size.y / image_size.y,
            )
            new_size = image_size * (
                min(ratios) if size == self.Size.FIT else max(ratios)
            )

            image = image.resize(new_size.to_tuple())
            cutout = Image.new(
                "RGBA", self.config.cutout_size.to_tuple(), self.config.background_color
            )
            cutout.paste(
                image,
                (
                    (self.config.cutout_size.x - new_size.x) // 2,
                    (self.config.cutout_size.y - new_size.y) // 2,
                ),
                image,
            )

        else:
            cutout = image

        cutout = cutout.rotate(
            self.config.rotation, expand=True, resample=Image.BICUBIC
        )

        return cutout

    def combine_images(
        self, template: Image.Image, processed: Image.Image
    ) -> Image.Image:
        template.paste(processed, self.config.position.to_tuple(), processed)
        return template

    def generate_image(self) -> Image.Image:
        image = self.frame_to_image_base()

        processed = self.process_image(image)

        template = Image.open(self.config.template_path)

        return self.combine_images(template, processed)


class PhotographStyle(TemplateStyle):
    name = "Look at this Canvas"
    id = 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: TemplateStyle.Config = self.Config(
            template_path="resources/templates/photograph.png",
            position=Coordinates(370, 147),
            rotation=15,
            cutout_size=Coordinates(185, 129),
            background_color=(35, 39, 42, 255),
        )

    def process_image(
        self, image: Image.Image, size: TemplateStyle.Size = TemplateStyle.Size.FILL
    ) -> Image.Image:
        return super().process_image(image, size)

    def combine_images(
        self, template: Image.Image, processed: Image.Image
    ) -> Image.Image:
        img = Image.new("RGBA", template.size, (255, 255, 255, 0))
        img.paste(processed, self.config.position.to_tuple(), processed)
        img.paste(template, (0, 0), template)
        return img


class DifferenceStyle(TemplateStyle):
    name = "Find the Difference"
    id = 31

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        path = "resources/templates/find_the_difference/" + choice(
            ["mona_lisa.png", "rplace.png", "starry_night.png"]
        )

        self.config: TemplateStyle.Config = self.Config(
            template_path=path,
            position=Coordinates(141, 51),
            cutout_size=Coordinates(413, 413),
            rotation=-10,
        )

    def get_color(self, pixel: Pixel) -> tuple[int, int, int, int]:
        color = pixel.color
        if color.code == "blank":
            return 71, 75, 107, 255
        return color.rgba


class WesternStyle(TemplateStyle):
    name = "Western"
    id = 11

    class Config(TemplateStyle.Config):
        def __init__(
            self,
            *args,
            font_path: str = "resources/fonts/WesternBangBang.otf",
            font_size_title: int = 80,
            font_size_subtitle: int = 60,
            font_color: tuple[int, int, int, int] = (51, 31, 18, 255),
            text_position_title: Coordinates = Coordinates(250, 180),
            text_position_subtitle: Coordinates = Coordinates(250, 100),
            **kwargs
        ):
            super().__init__(*args, **kwargs)

            self.font_path = font_path
            self.font_size_title = font_size_title
            self.font_size_subtitle = font_size_subtitle
            self.font_color = font_color
            self.text_position_title = text_position_title
            self.text_position_subtitle = text_position_subtitle

        @property
        def font_title(self) -> FreeTypeFont:
            return ImageFont.truetype(self.font_path, self.font_size_title)

        @property
        def font_subtitle(self) -> FreeTypeFont:
            return ImageFont.truetype(self.font_path, self.font_size_subtitle)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: WesternStyle.Config = self.Config(
            template_path="resources/templates/old_paper.png",
            position=Coordinates(56, 230),
            cutout_size=Coordinates(392, 411),
        )

    def to_sepia(self, rgba: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        r, g, b, a = rgba
        r = min(int(r * 0.393 + g * 0.769 + b * 0.189), 255)
        g = min(int(r * 0.349 + g * 0.686 + b * 0.168), 255)
        b = min(int(r * 0.272 + g * 0.534 + b * 0.131), 255)
        return r, g, b, a

    def get_color(self, pixel: Pixel) -> tuple[int, int, int, int]:
        color = pixel.color
        if color.id == 1:
            return 0, 0, 0, 0
        return self.to_sepia(color.rgba)

    def generate_image(self) -> Image.Image:
        self.base = super().generate_image()
        self.draw = ImageDraw.Draw(self.base)

        self.add_text(
            (
                self.frame.canvas.name
                if self.frame.has_special_text
                else "Blurple Canvas"
            ),
            self.config.font_subtitle,
            lambda text_size: (
                self.config.text_position_subtitle - text_size // 2
            ).to_tuple(),
            self.config.font_color,
        )

        self.add_text(
            self.frame.leading_text,
            self.config.font_title,
            lambda text_size: (
                self.config.text_position_title - text_size // 2
            ).to_tuple(),
            self.config.font_color,
        )

        return self.base
