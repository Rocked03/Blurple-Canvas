from PIL import Image, ImageFilter
from PIL.Image import Resampling

from objects.coordinates import Coordinates
from objects.styles.default import DefaultStyle


class CrunchyStyle(DefaultStyle):
    name = "Crunchy"
    id = 31

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_image(self) -> Image.Image:
        image = super().generate_image()

        size = Coordinates(*image.size)

        image = (
            image.resize((size // 8).to_tuple(), resample=Resampling.BOX)
            .filter(ImageFilter.SHARPEN)
            .filter(ImageFilter.SHARPEN)
            .resize(size.to_tuple(), resample=Resampling.BOX)
            .filter(ImageFilter.SHARPEN)
            .filter(ImageFilter.SHARPEN)
            .filter(ImageFilter.SHARPEN)
            .filter(ImageFilter.SHARPEN)
            .filter(ImageFilter.SHARPEN)
        )
        return image
