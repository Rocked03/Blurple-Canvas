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
    id = 10

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
            blur_radius_percent: int = 0.01,
            wave_frequency: float = 0.3,
            degree_detail=1,
            max_size: Coordinates = Coordinates.double(1000),
            *args,
            **kwargs
        ):
            super().__init__(*args, **kwargs)

            self.blur_radius_percent = blur_radius_percent
            self.wave_frequency = wave_frequency
            self.degree_detail = degree_detail
            self.max_size = max_size

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config = HolographicStyle.Config(
            background_color=(102, 135, 255, 180),
            font_color_title=(255, 255, 255, 220),
            font_color_subtitle=(185, 196, 237, 220),
            icon_opacity=220 / 255,
        )

        self.max_size = self.config.max_size

        seed = randint(0, 1000)
        np.random.seed(seed)
        self.noise_generator = OpenSimplex(seed=seed)
        self.noise: dict[float, float] = {}

    def generate_image(self) -> Image.Image:
        image = super().generate_image()

        blur_radius = self.config.blur_radius_percent * max(image.size)

        image = image.crop(
            (
                -blur_radius,
                -blur_radius,
                image.width + blur_radius,
                image.height + blur_radius,
            )
        )

        blur = image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
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
                lightness *= weight * 0.8 + 0.2

                alpha.putpixel((x, y), round(lightness))

        new_bands = bands[:3] + (alpha,)
        return Image.merge("RGBA", new_bands)

    def get_wave_weight(self, x: float) -> float:
        y = x + 60 % 180
        if x not in self.noise:
            self.noise[x] = (
                self.noise_generator.noise2(x * self.config.wave_frequency, 0) + 1
            ) / 2
        if y not in self.noise:
            self.noise[y] = (
                self.noise_generator.noise2(y * self.config.wave_frequency, 0) + 1
            ) / 2
        return self.noise[x] * self.noise[y]

    def angle_from_origin(self, xy: Coordinates, size: Coordinates) -> float:
        dx = xy.x - size.x / 2
        dy = size.y - xy.y - 1
        angle_deg = degrees(atan2(dy, dx))
        return round(
            angle_deg if angle_deg <= 180 else 360 - angle_deg,
            self.config.degree_detail,
        )

    def distance_from_origin(self, xy: Coordinates, size: Coordinates):
        return hypot(xy.x - size.x / 2, size.y - xy.y - 1)

    def distance_weight(self, distance: float, max_distance: float) -> float:
        return (distance**2) / (max_distance**2)

    def calculate_total_weight(
        self, wave_weight: float, distance_weight: float
    ) -> float:
        return 1 - (1 - wave_weight) * (distance_weight * 0.6)

    def get_color(self, pixel: Pixel) -> tuple[int, int, int, int]:
        color = pixel.color
        if color.id == 1:
            return 102, 135, 255, 0

        lightness = self.lightness(*color.rgb)
        lightness = lightness * 0.8 + 0.2

        r, g, b = 88, 100, 245

        lightness = round(lightness * 255)

        return r, g, b, lightness
