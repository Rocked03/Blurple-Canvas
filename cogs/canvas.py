import asyncio
import re
from functools import partial
from io import BytesIO
from typing import Optional, Callable

from PIL.Image import Image
from asyncpg import create_pool, Pool
from discord import app_commands, Interaction, User as UserDiscord, Client, File, Embed
from discord.app_commands import Choice
from discord.ext import commands
from discord.utils import utcnow

from config import POSTGRES_CREDENTIALS
from objects.cache import Cache
from objects.canvas import Canvas
from objects.coordinates import Coordinates
from objects.info import Info
from objects.palette import Palette
from objects.sqlManager import SQLManager
from objects.timer import Timer
from objects.user import User


def image_to_bytes_io(image: Image) -> BytesIO:
    bytes_io, size = image_to_bytes_io(image)
    return bytes_io


def image_to_bytes_io_with_size(image: Image) -> tuple[BytesIO, int]:
    buffer = BytesIO()
    image.save(buffer, "png")
    size = buffer.tell()
    buffer.seek(0)
    return buffer, size


def format_bytes(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
        if size < 1024:
            if unit == "B":
                return f"{size} B"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} YB"


def neutralise(txt: str) -> str:
    return "".join([c for c in txt.lower() if re.match(r"\w", c)])


class StartupEvents:
    def __init__(self):
        self.startup = asyncio.Event()
        self.sql = asyncio.Event()
        self.info = asyncio.Event()
        self.canvases = asyncio.Event()
        self.palette = asyncio.Event()

        asyncio.create_task(self.wait())

    async def wait(self):
        await self.sql.wait()
        await self.info.wait()
        await self.canvases.wait()
        await self.palette.wait()
        self.startup.set()


class CanvasCog(commands.Cog, name="Canvas"):
    """Canvas Module"""

    def __init__(self, bot):
        self.bot: Client = bot

        # Startup
        self.startup_events = StartupEvents()

        # SQL
        self.pool: Optional[Pool] = None
        self.bot.loop.create_task(self.startup_connect_sql())

        # Info
        self.info: Optional[Info] = None
        self.bot.loop.create_task(self.load_info())

        # Cache
        self.bot.loop.create_task(self.load_cache())

        # Canvases
        self.canvases: list[Canvas] = []
        self.bot.loop.create_task(self.load_canvases())

        # Colors
        self.palette: Optional[Palette] = None
        self.bot.loop.create_task(self.load_colors())

    # Startup methods
    async def wait_for_startup(self):
        await self.startup_events.startup.wait()

    async def startup_connect_sql(self):
        self.pool = await create_pool(**POSTGRES_CREDENTIALS)
        self.startup_events.sql.set()
        print("Connected to PostgreSQL database")

    async def sql(self) -> SQLManager:
        await self.startup_events.sql.wait()
        connection = await self.pool.acquire()
        self.bot.loop.create_task(self.timeout_connection(connection))
        return SQLManager(connection)

    async def timeout_connection(self, connection):
        await asyncio.sleep(600)
        await self.pool.release(connection)

    async def load_info(self):
        sql = await self.sql()
        self.info = await sql.fetch_info()
        await sql.close()
        self.startup_events.info.set()

    async def load_cache(self):
        sql = await self.sql()
        info = await sql.fetch_info()
        cache = await sql.fetch_canvas_by_event(
            info.current_event_id, info.cached_canvas_ids
        )
        await sql.close()

        for canvas in cache:
            if canvas.id not in self.bot.cache:
                print(f"Loading cache for canvas {canvas.name} ({canvas.id})")
                self.bot.cache[canvas.id] = Cache(await self.sql(), canvas=canvas)

    async def load_canvases(self):
        sql = await self.sql()
        self.canvases = list(await sql.fetch_canvas_all())
        await sql.close()
        self.startup_events.canvases.set()

    async def load_colors(self):
        sql = await self.sql()
        self.palette = await sql.fetch_colors_by_participation()
        await sql.close()
        self.startup_events.palette.set()

    # Fetch methods
    async def find_canvas(self, user_id) -> tuple[User, Canvas]:
        sql = await self.sql()
        await self.wait_for_startup()
        user = await sql.fetch_user(user_id)
        if user.current_canvas is None:
            await sql.close()
            raise ValueError(
                "You have not joined a canvas! Please use `/join` to join a canvas."
            )
        canvas = await sql.fetch_canvas_by_id(user.current_canvas.id)
        await sql.close()
        if canvas is None:
            raise ValueError("Cannot find your canvas. Please `/join` a canvas.")
        return user, canvas

    async def get_available_colors(self, guild_id: int):
        await self.wait_for_startup()
        return self.palette.get_available_colors(guild_id, self.info.current_event_id)

    async def sort_canvases(self) -> list[Canvas]:
        await self.wait_for_startup()
        canvases = sorted(
            sorted(
                sorted(self.canvases, key=lambda canvas: canvas.name),
                key=lambda canvas: not canvas.event_id == self.info.current_event_id,
            ),
            key=lambda canvas: canvas.locked,
        )
        return canvases

    # Helper methods
    async def async_image(
        self, function: Callable, *args, file_name: str, **kwargs
    ) -> tuple[File, str, int]:
        image = await self.bot.loop.run_in_executor(
            None, partial(function, *args, **kwargs)
        )
        bytes_io, size_bytes = await self.bot.loop.run_in_executor(
            None, image_to_bytes_io_with_size, image
        )
        file = File(bytes_io, filename=file_name)
        return file, f"attachment://{file_name}", size_bytes

    def base_embed(
        self, *, user: UserDiscord = None, title: str = None, color: int = None
    ):
        embed = Embed(
            title=title, timestamp=utcnow(), color=color or self.info.highlight_color
        )
        embed.set_footer(
            text=f"{f'{user} • ' if user else ''}" f"{self.bot.user.name}",
            icon_url=self.bot.user.avatar,
        )
        return embed

    # Autocomplete methods
    async def autocomplete_canvas(self, interaction, current: str):
        canvases = await self.sort_canvases()

        options_dict = {
            canvas.name + (" (read-only)" if canvas.locked else ""): canvas
            for canvas in canvases
        }

        if current:
            filtered = {
                name: value
                for name, value in options_dict.items()
                if neutralise(current) in neutralise(name)
                or current.isdigit()
                and value.id == int(current)
            }
        else:
            filtered = options_dict

        return [
            Choice(name=name, value=str(canvas.id)) for name, canvas in filtered.items()
        ]

    # Commands
    @app_commands.command(name="view")
    async def view(
        self, interaction: Interaction, x: int = None, y: int = None, zoom: int = 25
    ):
        """View the canvas"""
        if (x is None) != (y is None):
            return await interaction.response.send_message(
                "Please provide both x and y coordinates."
            )

        await interaction.response.defer()
        sql = await self.sql()

        try:
            timer = Timer()
            user, canvas = await self.find_canvas(interaction.user.id)

            if canvas.id in self.bot.cache:
                canvas = await self.bot.cache[canvas.id].get_canvas()

            # Get frame
            if not any([x, y]):
                frame = await canvas.get_frame_full(sql)
            else:
                frame = await canvas.get_frame_from_coordinate(
                    sql, Coordinates(x, y), zoom
                )
            await sql.close()

        except ValueError as e:
            await sql.close()
            return await interaction.followup.send(str(e), ephemeral=True)

        # Generate image
        max_size = Coordinates(2500, 2500)
        file, file_name, size_bytes = await self.async_image(
            frame.generate_image,
            max_size=max_size,
            file_name=f"canvas_{canvas.name_safe()}_{x}-{y}.png",
        )

        # Embed
        embed = self.base_embed(
            user=interaction.user,
            title=f"{self.info.title} • {canvas.name} {Coordinates(x, y) if x and y else ''}",
        )
        timer.mark_msg(f"Generated image ({format_bytes(size_bytes)})")
        await interaction.followup.send(
            embed=embed,
            file=file,
        )

    @app_commands.command(name="place")
    async def place(self, interaction: Interaction, x: int, y: int, color: str = None):
        """Place a pixel on the canvas"""
        await interaction.response.defer()
        sql = await self.sql()

        timer = Timer()

        try:
            user, canvas = await self.find_canvas(interaction.user.id)
        except ValueError as e:
            await sql.close()
            return await interaction.followup.send(str(e), ephemeral=True)

        if canvas.locked:
            await sql.close()
            return await interaction.followup.send(f"**{canvas.name}** is read-only.")

        coordinates = Coordinates(x, y)
        if coordinates not in canvas:
            await sql.close()
            return await interaction.followup.send(
                f"Coordinates {coordinates} are out of bounds."
            )

        if canvas.cooldown_length is not None:
            success, cooldown = await user.hit_cooldown(sql, canvas.cooldown_length)
            if not success:
                await sql.close()
                return await interaction.followup.send(
                    f"You are on cooldown. Please wait for {cooldown.time_left_strf()}.",
                    ephemeral=True,
                )

        colors = await self.get_available_colors(interaction.guild_id)
        if color is not None:
            if color not in colors:
                color = None
            else:
                color = colors[color]

        if canvas.id in self.bot.cache:
            canvas = await self.bot.cache[canvas.id].get_canvas()

        # 7 is max emoji limit
        frame = await canvas.get_frame_from_coordinate(sql, coordinates, 7, focus=True)

        emoji = frame.to_emoji(focus=self.palette.get_edit_color())

        embed = self.base_embed(
            user=interaction.user,
            title=f"Place Pixel • {canvas.name} {coordinates}",
        )
        embed.description = f"{emoji}"

        # ephemeral to avoid cooldown?
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="join")
    async def join(self, interaction: Interaction, canvas: str):
        """Join the canvas"""
        await interaction.response.defer()

        sql = await self.sql()
        user = await sql.fetch_user(interaction.user.id)
        canvas = await sql.fetch_canvas_by_name(canvas)

        if canvas is None:
            await sql.close()
            return await interaction.followup.send(f"Canvas '{canvas}' does not exist.")

        await user.set_current_canvas(sql, canvas)
        await sql.close()

        await interaction.followup.send(f"Joined canvas '{canvas.name}'")

    @join.autocomplete("canvas")
    async def join_autocomplete_canvas(self, interaction: Interaction, current: str):
        return await self.autocomplete_canvas(interaction, current)

    @app_commands.command(name="canvases")
    async def canvases(self, interaction: Interaction):
        """View all canvases"""
        canvases = await self.sort_canvases()

        canvas_names = [
            f"- **{canvas.name}**{' (read-only)' if canvas.locked else ''}"
            for canvas in canvases
        ]

        embed = self.base_embed(
            user=interaction.user,
            title="Canvas List",
        )

        embed.description = "\n".join(canvas_names)
        if not canvas_names:
            embed.description = "No canvases available."

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="palette")
    async def palette(self, interaction: Interaction, color: str = None):
        """View the palette"""
        pass

    @app_commands.command(name="toggle-skip")
    async def toggle_skip(self, interaction: Interaction):
        """Toggle skip confirm"""
        await interaction.response.defer()
        sql = await self.sql()
        user = await sql.fetch_user(interaction.user.id)
        await user.toggle_skip_confirm(sql)
        await sql.close()
        await interaction.followup.send(
            f"{'Enabled' if user.skip_confirm else 'Disabled'} place color confirmation.",
            ephemeral=True,
        )

    @app_commands.command(name="toggle-remind")
    async def toggle_remind(self, interaction: Interaction):
        """Toggle cooldown remind"""
        await interaction.response.defer()
        sql = await self.sql()
        user = await sql.fetch_user(interaction.user.id)
        await user.toggle_cooldown_remind(sql)
        await sql.close()
        await interaction.followup.send(
            f"{'Enabled' if user.cooldown_remind else 'Disabled'} cooldown reminder.",
            ephemeral=True,
        )

    @app_commands.command(name="stats")
    async def stats(self, interaction: Interaction, user: UserDiscord = None):
        """View user stats"""
        pass

    # Admin Commands
    admin_group = app_commands.Group(name="admin", description="Admin commands")

    @admin_group.command(name="lock-board")
    async def lock_board(self, interaction: Interaction, canvas: str):
        """Lock the canvas"""
        sql = await self.sql()
        canvas = await sql.fetch_canvas_by_name(canvas)
        if canvas is None:
            await sql.close()
            return await interaction.response.send_message(
                f"Canvas '{canvas}' does not exist."
            )

        if canvas.id in self.bot.cache:
            canvas = await self.bot.cache[canvas.id].get_canvas()
        await canvas.lock(sql)
        await sql.close()

        await interaction.response.send_message(f"Locked canvas '{canvas.name}'")

    @lock_board.autocomplete("canvas")
    async def lock_board_autocomplete_canvas(
        self, interaction: Interaction, current: str
    ):
        return await self.autocomplete_canvas(interaction, current)

    @admin_group.command(name="unlock-board")
    async def unlock_board(self, interaction: Interaction, canvas: str):
        """Unlock the canvas"""
        sql = await self.sql()
        canvas = await sql.fetch_canvas_by_name(canvas)
        if canvas is None:
            await sql.close()
            return await interaction.response.send_message(
                f"Canvas '{canvas}' does not exist."
            )

        if canvas.id in self.bot.cache:
            canvas = await self.bot.cache[canvas.id].get_canvas()
        await canvas.unlock(sql)
        await sql.close()

        await interaction.response.send_message(f"Unlocked canvas '{canvas.name}'")

    @unlock_board.autocomplete("canvas")
    async def unlock_board_autocomplete_canvas(
        self, interaction: Interaction, current: str
    ):
        return await self.autocomplete_canvas(interaction, current)

    # Admin commands
    # - Force refresh
    # - Partner stuff + colour stuff
    # - Blacklist
    # - Lock
    # - Create canvas
    # Imager stuff
    # - Frames
    # - Palette
    # Other stuff
    # - Cooldown reminder


async def setup(bot):
    await bot.add_cog(CanvasCog(bot))
