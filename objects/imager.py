from __future__ import annotations

import textwrap
from enum import Enum
from math import ceil
from typing import TYPE_CHECKING

from PIL import Image, ImageFont, ImageDraw

if TYPE_CHECKING:
    from objects.color import Palette, Color
    from objects.coordinates import Coordinates


class Imager:

    class Config:
        def __init__(self):
            self.blurple_rgb = (88, 101, 242)
            self.dark_blurple_rgb = (69, 79, 191)
            self.white = (255, 255, 255, 255)
            self.black = (0, 0, 0, 255)

        @staticmethod
        def font(size: int):
            return ImageFont.truetype("GintoNord-Black.otf", size)

        def blurple_rgba(self, alpha: int):
            return *self.blurple_rgb, alpha

        def dark_blurple_rgba(self, alpha: int):
            return *self.dark_blurple_rgb, alpha

    class PaletteConfig(Config):
        def __init__(self):
            super().__init__()
            self.square_size = 300
            self.border_width = 100

            self.name_width = 10

        @property
        def text_spacing(self):
            return round(self.square_size / 1.5)

        @property
        def inner_text_spacing(self):
            return round(self.square_size / 30)

        @property
        def edge_text_border(self):
            return round(self.square_size / 10)

        @property
        def base_corners(self):
            return self.square_size // 6

        @property
        def square_corners(self):
            return self.square_size // 6

        @property
        def font_color_title(self):
            return self.font(round(self.square_size / 2.5))

        @property
        def font_name(self):
            return self.font(round(self.square_size / 8.5))

        @property
        def font_code(self):
            return self.font(round(self.square_size / 10.5))

    @staticmethod
    def round_corner(radius: int, fill):
        """Draw a round corner"""
        corner = Image.new("RGBA", (radius, radius), (0, 0, 0, 0))
        draw = ImageDraw.Draw(corner)
        draw.pieslice(((0, 0), (radius * 2, radius * 2)), 180, 270, fill=fill)
        return corner

    @staticmethod
    def round_rectangle(
        size: tuple[int, int],
        radius: int,
        fill,
        *,
        top_left: bool = False,
        top_right: bool = False,
        bottom_left: bool = False,
        bottom_right: bool = False,
        all_corners: bool = False,
    ):
        """Draw a rounded rectangle"""
        if all_corners:
            top_left = top_right = bottom_left = bottom_right = True

        width, height = size
        rectangle = Image.new("RGBA", size, fill)
        corner = Imager.round_corner(radius, fill)
        if top_left:
            rectangle.paste(corner, (0, 0))
        if bottom_left:
            rectangle.paste(corner.rotate(90), (0, height - radius))
        if bottom_right:
            rectangle.paste(corner.rotate(180), (width - radius, height - radius))
        if top_right:
            rectangle.paste(corner.rotate(270), (width - radius, 0))
        return rectangle

    class PaletteCategories(Enum):
        ALL = (8, "All")
        GLOBAL = (6, "Main Colors")
        GUILD = (6, "Partner Colors")

    @staticmethod
    def palette_to_image(palette: Palette, category: PaletteCategories) -> Image.Image:
        config = Imager.PaletteConfig()

        height = (
            config.border_width * (3 if category == Imager.PaletteCategories.ALL else 2)
            + config.text_spacing
            * (2 if category == Imager.PaletteCategories.ALL else 1)
            + config.square_size
            * (
                ceil(palette.global_count / category.value[0])
                + ceil(palette.guild_count / category.value[0])
            )
        )

        width = 2 * config.border_width + config.square_size * category.value[0]

        image = Imager.round_rectangle(
            (width, height),
            config.base_corners,
            config.blurple_rgba(75),
            all_corners=True,
        )

        from objects.color import Palette

        spacer = 0
        if (
            category == Imager.PaletteCategories.ALL
            or category == Imager.PaletteCategories.GLOBAL
        ):
            global_palette = Imager.palette_image_subsection(
                Palette(palette.get_global_colors()),
                category,
                Imager.PaletteCategories.GLOBAL.value[1],
                config=config,
            )
            image.paste(
                global_palette,
                (config.border_width, config.border_width + spacer),
                global_palette,
            )
            spacer += global_palette.height + config.border_width

        if (
            category == Imager.PaletteCategories.ALL
            or category == Imager.PaletteCategories.GUILD
        ):
            guild_palette = Imager.palette_image_subsection(
                Palette(palette.get_guild_colors()),
                category,
                Imager.PaletteCategories.GUILD.value[1],
                config=config,
            )
            image.paste(
                guild_palette,
                (config.border_width, config.border_width + spacer),
                guild_palette,
            )

        return image

    @staticmethod
    def palette_image_subsection(
        palette: Palette,
        category: PaletteCategories,
        title: str,
        *,
        config: PaletteConfig = PaletteConfig(),
    ) -> Image.Image:
        n_height = ceil(palette.total_count / category.value[0])
        bg = Imager.round_rectangle(
            (
                category.value[0] * config.square_size,
                config.text_spacing + config.square_size * n_height,
            ),
            config.square_corners,
            config.dark_blurple_rgba(255),
            all_corners=True,
        )
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(bg)

        text_bbox = config.font_color_title.getbbox(text=title)

        draw.text(
            (
                round((bg.width - text_bbox[2]) / 2),
                round((config.text_spacing - text_bbox[3]) / 2),
            ),
            title,
            font=config.font_color_title,
            fill=config.white,
        )

        from objects.coordinates import Coordinates

        rows: dict[Coordinates, Color] = {}
        for i, color in enumerate(palette.sorted()):
            row = i % category.value[0]
            col = i // category.value[0]
            rows[Coordinates(row, col)] = color

        for coord, color in rows.items():
            x = coord.x * config.square_size
            y = config.text_spacing + coord.y * config.square_size
            color_square = Imager.color_to_image(
                color,
                rounded_corners=(
                    False,
                    False,
                    coord.x == 0 and coord.y == n_height - 1,
                    coord.x == category.value[0] - 1 and coord.y == n_height - 1,
                ),
                config=config,
            )

            bg.paste(color_square, (x, y))

        return bg

    @staticmethod
    def color_to_image(
        color: Color,
        *,
        rounded_corners: tuple[bool, bool, bool, bool] = None,
        config: PaletteConfig = PaletteConfig(),
    ):
        if rounded_corners is None:
            rounded_corners = (True, True, True, True)
        color_square = Imager.round_rectangle(
            (config.square_size, config.square_size),
            config.square_corners,
            color.rgba,
            top_left=rounded_corners[0],
            top_right=rounded_corners[1],
            bottom_left=rounded_corners[2],
            bottom_right=rounded_corners[3],
        )
        square_draw = ImageDraw.Draw(color_square)
        text_color = config.black if color.to_hsl[2] == 1 else config.white
        color_name = "\n".join(textwrap.wrap(color.name, config.name_width))
        text_size = square_draw.multiline_textbbox(
            text=color_name,
            xy=(0, 0),
            font=config.font_name,
            align="center",
            spacing=config.inner_text_spacing,
        )
        square_draw.multiline_text(
            (
                round((config.square_size - text_size[2]) / 2),
                round((config.square_size - text_size[3]) / 2),
            ),
            color_name,
            font=config.font_name,
            fill=text_color,
            align="center",
            spacing=config.inner_text_spacing,
        )
        text_rgb = ", ".join(map(str, color.rgba[:3]))
        text_size = config.font_code.getbbox(text_rgb)
        square_draw.text(
            (
                round((config.square_size - text_size[2]) / 2),
                config.edge_text_border,
            ),
            text_rgb,
            font=config.font_code,
            fill=text_color,
        )
        text_size = config.font_code.getbbox(color.code)
        square_draw.text(
            (
                round((config.square_size - text_size[2]) / 2),
                config.square_size - config.edge_text_border - text_size[3],
            ),
            color.code,
            font=config.font_code,
            fill=text_color,
        )
        return color_square
