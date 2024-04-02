from PIL import Image

from objects.coordinates import Coordinates
from objects.style import Style, Config


class TemplateStyle(Style):
    class Config(Config):
        def __init__(self, *args, template_path: str, position: Coordinates, **kwargs):
            super().__init__(*args, **kwargs)

            self.template_path = template_path
            self.position = position

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: TemplateStyle.Config = None

    def process_image(self, image: Image.Image) -> Image.Image:
        raise NotImplementedError

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

    class Config(TemplateStyle.Config):
        def __init__(
            self,
            *args,
            cutout_size: Coordinates = Coordinates(185, 129),
            rotation: int = 15,
            background_color: tuple[int, int, int, int] = (35, 39, 42, 255),
            **kwargs
        ):
            super().__init__(*args, **kwargs)

            self.cutout_size = cutout_size
            self.rotation = rotation
            self.background_color = background_color

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: PhotographStyle.Config = self.Config(
            template_path="resources/templates/photograph.png",
            position=Coordinates(370, 147),
        )

    def process_image(self, image: Image.Image) -> Image.Image:
        size = Coordinates(*image.size)
        new_size = size * min(
            self.config.cutout_size.x / size.x,
            self.config.cutout_size.y / size.y,
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
        cutout = cutout.rotate(
            self.config.rotation, expand=True, resample=Image.BICUBIC
        )

        return cutout

    def combine_images(
        self, template: Image.Image, processed: Image.Image
    ) -> Image.Image:
        img = Image.new("RGBA", template.size, (255, 255, 255, 0))
        img.paste(processed, self.config.position.to_tuple(), processed)
        img.paste(template, (0, 0), template)
        return img
