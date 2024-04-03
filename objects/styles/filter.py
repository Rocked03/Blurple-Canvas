from colorsys import hls_to_rgb, hsv_to_rgb
from math import degrees, atan2, hypot
from random import randint

import numpy as np
from PIL import Image, ImageFilter
from PIL.Image import Resampling
from opensimplex import OpenSimplex

from objects.color import Color
from objects.coordinates import Coordinates
from objects.pixel import Pixel
from objects.style import Style, Config
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


class HolographicStyle(DefaultStyle):
    name = "Holographic"
    id = 12

    class Config(DefaultStyle.Config):
        def __init__(
            self,
            hue: int = 227 / 360,
            saturation: float = 0.60,
            blur_radius: int = 30,
            *args,
            **kwargs
        ):
            super().__init__(*args, **kwargs)

            self.hue = hue
            self.saturation = saturation
            self.blur_radius = blur_radius

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = HolographicStyle.Config(
            background_color=(102, 135, 255, 180),
            font_color_title=(255, 255, 255, 220),
            font_color_subtitle=(185, 196, 237, 220),
            icon_opacity=220 / 255,
        )

        self.max_size = Coordinates.double(1000)

        self.wave_frequency = 0.6
        self.degree_detail = 1
        seed = randint(0, 1000)
        np.random.seed(seed)
        self.noise_generator = OpenSimplex(seed=seed)
        self.noise: dict[float, float] = {}

    def generate_image(self) -> Image.Image:
        image = super().generate_image()

        image = image.crop(
            (
                -self.config.blur_radius,
                -self.config.blur_radius,
                image.width + self.config.blur_radius,
                image.height + self.config.blur_radius,
            )
        )

        blur = image.filter(ImageFilter.GaussianBlur(radius=self.config.blur_radius))
        blur = self.multiply_opacity(blur, 0.8)

        blur.paste(image, (0, 0), image)

        final = self.apply_wave(blur)

        return final

    def lightness(self, r, g, b) -> float:
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255

    def apply_wave(self, image: Image.Image):
        bands = image.split()
        alpha = bands[3]

        size = Coordinates(image.width, image.height)
        max_distance = self.distance_from_origin(Coordinates(0, 0), size)

        for x in range(image.width):
            for y in range(image.height):

                coordinates = Coordinates(x, y)
                angle = self.angle_from_origin(coordinates, size)
                distance = self.distance_from_origin(coordinates, size)
                weight = self.calculate_total_weight(
                    self.get_wave_weight(angle),
                    self.distance_weight(distance, max_distance),
                )

                lightness = alpha.getpixel((x, y))
                lightness *= weight * 0.5 + 0.5

                alpha.putpixel((x, y), round(lightness))

        new_bands = bands[:3] + (alpha,)
        return Image.merge("RGBA", new_bands)

    def get_wave_weight(self, x: float) -> float:
        if x not in self.noise:
            self.noise[x] = (
                self.noise_generator.noise2(x * self.wave_frequency, 0) + 1
            ) / 2
        return self.noise[x]

    def angle_from_origin(self, xy: Coordinates, size: Coordinates) -> float:
        dx = xy.x - size.x / 2
        dy = size.y - xy.y - 1
        angle_deg = degrees(atan2(dy, dx))
        return round(
            angle_deg if angle_deg <= 180 else 360 - angle_deg, self.degree_detail
        )

    def distance_from_origin(self, xy: Coordinates, size: Coordinates):
        return hypot(xy.x - size.x / 2, size.y - xy.y - 1)

    def distance_weight(self, distance: float, max_distance: float) -> float:
        return (distance**2) / (max_distance**2)

    def calculate_total_weight(
        self, wave_weight: float, distance_weight: float
    ) -> float:
        return 1 - (1 - wave_weight) * distance_weight

    def get_color(self, pixel: Pixel) -> tuple[int, int, int, int]:
        color = pixel.color
        if color.id == 1:
            return 102, 135, 255, 0

        lightness = self.lightness(*color.rgb)
        lightness = lightness * 0.8 + 0.2

        r, g, b = hsv_to_rgb(self.config.hue, self.config.saturation, lightness)

        r = round(r * 255)
        g = round(g * 255)
        b = round(b * 255)
        lightness = round(lightness * 255)

        return r, g, b, lightness
