import asyncio
import re
import traceback
from functools import partial
from io import BytesIO
from typing import Optional, Callable

import numpy
from PIL import Image
from asyncpg import create_pool, Pool, UniqueViolationError
from discord import (
    app_commands,
    Interaction,
    User as UserDiscord,
    Client,
    File,
    Embed,
    Message,
    Attachment,
)
from discord.app_commands import Choice
from discord.ext import commands
from discord.utils import utcnow

from config import POSTGRES_CREDENTIALS
from objects.cache import Cache
from objects.canvas import Canvas
from objects.color import Palette, Color
from objects.cooldownManager import CooldownManager
from objects.coordinates import Coordinates
from objects.event import Event
from objects.info import Info
from objects.guild import Participation
from objects.pixel import Pixel
from objects.sqlManager import SQLManager
from objects.stats import Leaderboard
from objects.timer import Timer
from objects.user import User
from objects.views import (
    ConfirmEnum,
    NavigationEnum,
    NavigateView,
    PaletteView,
    ConfirmView,
)


def admin_check():
    async def check(interaction: Interaction):
        return await interaction.client.info.check_perms(interaction)

    return app_commands.check(check)


def image_to_bytes_io(image: Image.Image) -> BytesIO:
    bytes_io, _ = image_to_bytes_io_with_size(image)
    return bytes_io


def image_to_bytes_io_with_size(image: Image.Image) -> tuple[BytesIO, int]:
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
        print("Startup complete")


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

        # Cooldown Manager
        self.bot.cooldown_manager = CooldownManager()
        self.bot.loop.create_task(self.tidy_cooldown_scheduler())

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
        return SQLManager(connection, self.bot)

    async def timeout_connection(self, connection):
        await asyncio.sleep(600)
        await self.pool.release(connection)

    async def load_info(self):
        sql = await self.sql()
        self.info = await sql.fetch_info()
        self.bot.info = self.info
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
                self.bot.cache[canvas.id] = Cache(await self.sql(), canvas=canvas)

    async def load_canvases(self):
        sql = await self.sql()
        self.canvases = list(await sql.fetch_canvas_all())
        await sql.close()
        self.startup_events.canvases.set()

    async def load_colors(self):
        sql = await self.sql()
        await self.startup_events.info.wait()
        self.palette = await sql.fetch_colors_by_participation(
            self.info.current_event_id
        )
        await sql.close()
        self.startup_events.palette.set()

    async def tidy_cooldown_scheduler(self):
        await self.wait_for_startup()
        while True:
            sql = await self.sql()
            await sql.trigger_delete_surpassed_cooldowns()
            await sql.close()
            await asyncio.sleep(3600)

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
        await sql.close()
        canvas = user.current_canvas
        if canvas is None:
            raise ValueError("Cannot find your canvas. Please `/join` a canvas.")
        return user, canvas

    async def fetch_canvas_by_name(self, sql: SQLManager, name: str) -> Canvas:
        canvas = await sql.fetch_canvas_by_name(name)
        if canvas is None:
            raise ValueError(f"Canvas '{canvas}' does not exist.")

        canvas = await self.check_cache(canvas)
        return canvas

    async def check_cache(self, canvas: Canvas):
        if canvas.id in self.bot.cache:
            canvas = await self.bot.cache[canvas.id].get_canvas()
        return canvas

    async def get_available_colors(self, guild_id: int = None) -> Palette:
        await self.wait_for_startup()
        return self.palette.get_available_colors_as_palette(
            guild_id, self.info.current_event_id
        )

    async def sort_canvases(self) -> list[Canvas]:
        await self.wait_for_startup()
        canvases = sorted(
            sorted(
                sorted(self.canvases, key=lambda canvas: canvas.name),
                key=lambda canvas: canvas.event is None
                or not canvas.event.id == self.info.current_event_id,
            ),
            key=lambda canvas: canvas.locked,
        )
        return canvases

    # Helper methods

    async def async_image_bytes(
        self, function: Callable, *args, **kwargs
    ) -> tuple[BytesIO, int]:
        image = await self.bot.loop.run_in_executor(
            None, partial(function, *args, **kwargs)
        )
        return image_to_bytes_io_with_size(image)

    async def async_image(
        self, function: Callable, *args, file_name: str, **kwargs
    ) -> tuple[File, str, int]:
        bytes_io, size_bytes = await self.async_image_bytes(function, *args, **kwargs)
        file = File(bytes_io, filename=file_name)
        return file, f"attachment://{file_name}", size_bytes

    def base_embed(
        self,
        *,
        user: UserDiscord = None,
        title: str = None,
        color: int = None,
        footer: str = None,
    ):
        embed = Embed(
            title=title, timestamp=utcnow(), color=color or self.info.highlight_color
        )
        footer_text = f"{f'{user} • ' if user else ''}" f"{self.bot.user.name}"
        embed.set_footer(
            text=(footer + " • " if footer else "") + footer_text,
            icon_url=self.bot.user.avatar,
        )
        return embed

    # Autocomplete methods

    async def autocomplete_canvas(self, _, current: str):
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

    async def autocomplete_color(self, _, current, colors: list[Color] = None):
        return [
            Choice(name=color.name, value=str(color.id))
            for color in (colors if colors else self.palette.sorted())
            if neutralise(current) in neutralise(color.name)
            or neutralise(current) in neutralise(color.code)
            or current.isdigit()
            and color.id == int(current)
        ][:25]

    async def cog_app_command_error(self, interaction: Interaction, error: Exception):
        ignored = (
            commands.CommandNotFound,
            commands.CheckFailure,
            commands.CommandInvokeError,
        )
        if isinstance(error, ignored):
            return
        elif isinstance(error, commands.CommandError):
            await interaction.response.send_message(str(error), ephemeral=True)
        else:
            traceback.print_exc()
            raise error

    @app_commands.command(name="view")
    @app_commands.describe(
        x="x coordinate",
        y="y coordinate",
        zoom="Zoom level (default 25)",
    )
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

            canvas = await self.check_cache(canvas)

            # Get frame
            if not any([x, y]):
                frame = await canvas.get_frame_full(sql)
            else:
                frame = await canvas.get_frame_from_coordinate(
                    sql, canvas.get_true_coordinates(x, y), zoom
                )
            await sql.close()

        except ValueError as e:
            await sql.close()
            return await interaction.followup.send(str(e), ephemeral=True)

        # Generate image
        max_size = Coordinates(3000, 3000)
        file, file_name, size_bytes = await self.async_image(
            frame.generate_image,
            max_size=max_size,
            file_name=f"canvas_{canvas.name_safe}_{x}-{y}.png",
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
    @app_commands.describe(
        x="x coordinate",
        y="y coordinate",
        color="Color to place. Leave blank to select from dropdown.",
    )
    async def place(self, interaction: Interaction, x: int, y: int, color: str = None):
        """Place a pixel on the canvas"""
        sql = await self.sql()

        try:
            user, canvas = await self.find_canvas(interaction.user.id)
        except ValueError as e:
            await sql.close()
            return await interaction.response.send_message(str(e), ephemeral=True)

        await interaction.response.defer()

        if user.is_blacklisted:
            await sql.close()
            return await interaction.followup.send(
                "You are blacklisted.", ephemeral=True
            )

        if canvas.locked:
            await sql.close()
            return await interaction.followup.send(f"**{canvas.name}** is read-only.")

        coordinates = canvas.get_true_coordinates(x, y)
        if coordinates not in canvas:
            await sql.close()
            return await interaction.followup.send(
                f"Coordinates {canvas.get_f_coordinates(coordinates)} are out of bounds."
            )

        cooldown = None
        if canvas.cooldown_length is not None:
            success, cooldown = await user.hit_cooldown_with_message(
                sql, canvas, interaction.channel
            )
            if not success:
                await sql.close()
                return await interaction.followup.send(
                    f"You are on cooldown. You can place another pixel {cooldown.time_left_markdown}.",
                    ephemeral=True,
                )

        color = (await self.get_available_colors())[color]
        if color is not None:
            if not color.is_valid(interaction.guild_id, self.info.current_event_id):
                await sql.close()
                return await interaction.followup.send(
                    f"{color.name} is not available in this guild."
                )

        canvas = await self.check_cache(canvas)

        # 11 is max emoji limit
        zoom = 11
        frame = await canvas.get_frame_from_coordinate(
            sql, coordinates, zoom, focus=True
        )

        msg: Optional[Message] = None

        async def send_msg(msg_: Message, *args, **kwargs):
            if msg_ is None:
                return await interaction.followup.send(*args, **kwargs)
            else:
                kwargs.pop("ephemeral", None)
                await msg_.edit(*args, **kwargs)
                return msg_

        embed = self.base_embed(user=interaction.user)
        view: Optional[ConfirmView] = None
        suffix = f"{canvas.name} {canvas.get_f_coordinates(coordinates)}"

        if not user.skip_confirm or not color:
            old_view: Optional[ConfirmView] = None
            if not user.skip_confirm:
                # Navigating pixels
                while True:
                    embed.title = f"Place pixel • {suffix}"
                    embed.description = frame.to_emoji(
                        focus=self.palette.edit_color, new_color=color
                    )

                    view: NavigateView = NavigateView(
                        interaction.user.id,
                        disabled_directions=[
                            direction
                            for direction in NavigationEnum
                            if not (coordinates + direction.value) in canvas.bbox
                        ],
                    )
                    msg = await send_msg(msg, embed=embed, view=view)
                    if old_view:
                        await old_view.defer()

                    timeout = await view.wait()

                    if timeout or view.confirm == ConfirmEnum.CANCEL:
                        if timeout:
                            embed.title = f"Timed out • {suffix}"
                        elif view.confirm == ConfirmEnum.CANCEL:
                            embed.title = f"Cancelled • {suffix}"
                        await send_msg(msg, embed=embed, view=None)
                        await view.defer()
                        if cooldown is not None:
                            await user.clear_cooldown(sql, cooldown)
                        await sql.close()
                        return

                    elif view.confirm == ConfirmEnum.CONFIRM:
                        old_view = view
                        break

                    else:
                        coordinates += view.direction.value
                        frame = await canvas.get_frame_from_coordinate(
                            sql, coordinates, zoom, focus=True
                        )
                        old_view = view

                    suffix = f"{canvas.name} {canvas.get_f_coordinates(coordinates)}"

            if not color:
                # Selecting color
                embed.title = f"Select color • {suffix}"
                embed.description = frame.to_emoji(focus=self.palette.edit_color)

                view: PaletteView = PaletteView(
                    await self.get_available_colors(interaction.guild_id),
                    interaction.user.id,
                )
                msg = await send_msg(msg, embed=embed, view=view)
                await old_view.defer() if old_view else None

                timeout = await view.wait()

                if (
                    timeout
                    or view.confirm == ConfirmEnum.CANCEL
                    or not view.dropdown.values
                ):
                    if timeout:
                        embed.title = f"Timed out • {suffix}"
                    elif view.confirm == ConfirmEnum.CANCEL:
                        embed.title = f"Cancelled • {suffix}"
                    elif not view.dropdown.values:
                        embed.title = f"No color selected • {suffix}"
                    await send_msg(msg, embed=embed, view=None)
                    await view.defer()
                    if cooldown is not None:
                        await user.clear_cooldown(sql, cooldown)
                    await sql.close()
                    return

                color = self.palette[view.dropdown.values[0]]

        # Place pixel
        await canvas.place_pixel(
            sql, user=user, xy=coordinates, color=color, guild_id=interaction.guild_id
        )
        frame = await canvas.regenerate_frame(sql, frame)
        embed.title = f"Placed pixel • {suffix}"
        embed.description = frame.to_emoji()
        if view is not None:
            await send_msg(msg, embed=embed, view=None)
        else:
            await send_msg(msg, embed=embed)

    @place.autocomplete("color")
    async def place_autocomplete_color(self, interaction: Interaction, current: str):
        return await self.autocomplete_color(
            interaction,
            current,
            (await self.get_available_colors(interaction.guild_id)).sorted(),
        )

    @app_commands.command(name="join")
    @app_commands.describe(canvas="Canvas to join")
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
    @app_commands.describe(
        palette="Palette selection",
        color="Specific color to view",
    )
    async def palette(
        self, interaction: Interaction, palette: str = "all", color: str = None
    ):
        """View the palette"""
        await interaction.response.defer()

        if color:
            color = self.palette[color]
            if not color:
                return await interaction.followup.send("Invalid color.")
            file, file_name, size_bytes = await self.async_image(
                color.to_image,
                file_name=f"{neutralise(color.name.replace(' ', '_'))}.png",
            )
            embed = self.base_embed(
                user=interaction.user,
                title=f"{color.name} • {color.code}",
                color=color.hex,
            )
            embed.description = (
                "This is a global color! It is available to use everywhere."
                if color.is_global
                else "This is an exclusive color! It is only available in "
                + color.guild.invite_url_masked_markdown(
                    f"__**{color.guild.guild.name}**__"
                    if color.guild.guild
                    else "__its' own partner server__"
                )
                + "."
            )

            embed.set_image(url=file_name)
            await interaction.followup.send(embed=embed, file=file)

        else:
            if palette == "all":
                file, file_name, size_bytes = await self.async_image(
                    self.palette.to_image_all,
                    self.info.current_event_id,
                    file_name="palette.png",
                )
            elif palette == "global":
                file, file_name, size_bytes = await self.async_image(
                    self.palette.to_image_global, file_name="palette.png"
                )
            elif palette == "guild":
                file, file_name, size_bytes = await self.async_image(
                    self.palette.to_image_guild,
                    self.info.current_event_id,
                    file_name="palette.png",
                )
            else:
                return await interaction.followup.send("Invalid palette type.")

            embed = self.base_embed(
                user=interaction.user, title="Blurple Canvas Palette"
            )
            embed.set_image(url=file_name)
            await interaction.followup.send(embed=embed, file=file)

    @palette.autocomplete("palette")
    async def palette_autocomplete_palette(self, _: Interaction, __: str):
        return [
            Choice(name="All", value="all"),
            Choice(name="Global", value="global"),
            Choice(name="Partner", value="guild"),
        ]

    @palette.autocomplete("color")
    async def palette_autocomplete_color(self, interaction: Interaction, current: str):
        return await self.autocomplete_color(interaction, current)

    @app_commands.command(name="toggle-skip")
    async def toggle_skip(self, interaction: Interaction):
        """Toggle skipping placing confirmation"""
        await interaction.response.defer(ephemeral=True)
        sql = await self.sql()
        user = await sql.fetch_user(interaction.user.id)
        await user.toggle_skip_confirm(sql)
        await sql.close()
        await interaction.followup.send(
            f"{'Enabled' if not user.skip_confirm else 'Disabled'} "
            f"placing confirmation.",
        )

    @app_commands.command(name="toggle-remind")
    async def toggle_remind(self, interaction: Interaction):
        """Toggle cooldown reminders"""
        await interaction.response.defer()
        sql = await self.sql()
        user = await sql.fetch_user(interaction.user.id)
        await user.toggle_cooldown_remind(sql)
        await sql.close()
        await interaction.followup.send(
            f"{'Enabled' if user.cooldown_remind else 'Disabled'} cooldown reminder.",
            ephemeral=True,
        )

    stats_group = app_commands.Group(name="stats", description="Stats commands")

    @stats_group.command(name="me")
    @app_commands.describe(user="User to view stats for. Leave blank to view your own.")
    async def stats_me(self, interaction: Interaction, user: UserDiscord = None):
        """View your own stats. If you mention a user, view their stats instead."""
        if user is None:
            user = interaction.user

        sql = await self.sql()

        try:
            _, canvas = await self.find_canvas(interaction.user.id)
        except ValueError as e:
            await sql.close()
            return await interaction.response.send_message(str(e), ephemeral=True)

        await interaction.response.defer()

        stats = await sql.fetch_user_stats(user.id, canvas.id)
        await sql.close()

        if stats is None:
            return await interaction.followup.send(
                f"I couldn't find any stats for you in {canvas.name}!"
            )

        embed = self.base_embed(
            user=user, title=f"{user}'s stats", footer=f"{canvas.id}"
        )
        embed.description = f"Showing stats in **{canvas.name}**"

        embed.add_field(name="Pixels placed", value=f"{stats.total_pixels:,}")
        embed.add_field(
            name="Total pixels leaderboard", value=f"{stats.ranking_ordinal} place"
        )
        embed.add_field(
            name="Most frequent color placed",
            value=stats.most_frequent_color_formatted,
        )

        await interaction.followup.send(embed=embed)

    @stats_group.command(name="guild")
    @app_commands.describe(
        guild_id="ID of guild to view stats for. Leave blank to view this current server."
    )
    async def stats_guild(self, interaction: Interaction, guild_id: str = None):
        """View guild stats"""
        if not guild_id:
            guild = interaction.guild
            guild_id = guild.id
        else:
            if not guild_id.isdigit():
                return await interaction.response.send_message(
                    "Invalid guild ID.", ephemeral=True
                )
            else:
                guild_id = int(guild_id)

            guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else str(guild_id)

        sql = await self.sql()

        try:
            _, canvas = await self.find_canvas(interaction.user.id)
        except ValueError as e:
            await sql.close()
            return await interaction.response.send_message(str(e), ephemeral=True)

        await interaction.response.defer()

        if canvas.event is None:
            await sql.close()
            return await interaction.followup.send(
                "Cannot show guild stats for canvases without events."
            )

        stats = await sql.fetch_guild_stats(guild_id, canvas.id)

        if stats is None:
            return await interaction.followup.send(
                f"I couldn't find any stats for this guild ({guild_name}) in {canvas.name}!"
            )

        await stats.load_leaderboard(sql, max_rank=5, limit=5)

        embed = self.base_embed(
            user=interaction.user,
            title=f"{guild_name}'s stats",
            footer=f"{canvas.id}",
        )

        embed.description = f"Showing stats in **{canvas.name}**"

        embed.add_field(name="Total pixels placed", value=f"{stats.total_pixels:,}")

        embed.add_field(
            name="Most frequent color placed",
            value=stats.most_frequent_color_formatted,
        )

        if stats.leaderboard:
            await stats.leaderboard.load_colors(sql, canvas.id)
            embed.add_field(
                name="Leaderboard", value=stats.leaderboard.formatted(), inline=False
            )
        await sql.close()

        await interaction.followup.send(embed=embed)

    @stats_guild.autocomplete("guild_id")
    async def stats_leaderboard_autocomplete_guild_id(
        self, interaction: Interaction, current: str
    ):
        choices = [
            Choice(name=interaction.guild.name, value=""),
        ]
        if current.isdigit():
            guild = self.bot.get_guild(int(current))
            if guild:
                choices.append(Choice(name=guild.name, value=str(guild.id)))
        return choices

    @stats_group.command(name="leaderboard")
    @app_commands.describe(
        guild_id="ID of the guild to view the leaderboard for. Leave blank to view the global leaderboard.",
        include_yourself="Include yourself in the leaderboard? Default is True.",
    )
    async def stats_leaderboard(
        self,
        interaction: Interaction,
        guild_id: str = None,
        include_yourself: bool = True,
    ):
        """View the leaderboard"""
        user_id = interaction.user.id if include_yourself else None

        if not guild_id:
            guild = guild_id = guild_name = None
        else:
            if not guild_id.isdigit():
                return await interaction.response.send_message(
                    "Invalid guild ID.", ephemeral=True
                )
            else:
                guild_id = int(guild_id)
                guild = self.bot.get_guild(guild_id)
                guild_name = guild.name if guild else str(guild_id)

        try:
            _, canvas = await self.find_canvas(interaction.user.id)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

        await interaction.response.defer()

        sql = await self.sql()
        if guild_id:
            leaderboard = Leaderboard(
                await sql.fetch_leaderboard_guild(canvas.id, guild_id, user_id=user_id)
            )
        else:
            leaderboard = Leaderboard(
                await sql.fetch_leaderboard(canvas.id, user_id=user_id)
            )

        if not leaderboard:
            if guild_id:
                return await interaction.followup.send(
                    f"No leaderboard found for guild {guild_name} in *{canvas.name}*. "
                    + (
                        "I'm not in that guild, perhaps you entered the incorrect ID?"
                        if not guild
                        else "Better start placing some pixels!"
                    )
                )
            else:
                return await interaction.followup.send(
                    f"No global leaderboard found for *{canvas.name}*."
                )

        await leaderboard.load_colors(sql, canvas.id)
        await sql.close()

        embed = self.base_embed(
            user=interaction.user,
            title=f"{canvas.name} Leaderboard"
            + (f" • {guild_name}" if guild_id else ""),
        )
        embed.description = leaderboard.formatted(highlighted_user_id=user_id)

        await interaction.followup.send(embed=embed)

    @stats_leaderboard.autocomplete("guild_id")
    async def stats_leaderboard_autocomplete_guild_id(
        self, interaction: Interaction, current: str
    ):
        choices = [
            Choice(name="Global", value=""),
            Choice(name=interaction.guild.name, value=str(interaction.guild_id)),
        ]
        if current.isdigit():
            guild = self.bot.get_guild(int(current))
            if guild:
                choices.append(Choice(name=guild.name, value=str(guild.id)))
        return choices

    # Admin Commands

    admin_group = app_commands.Group(name="admin", description="Admin commands")

    admin_canvas_group = app_commands.Group(
        name="canvas", description="Canvas commands", parent=admin_group
    )

    @admin_canvas_group.command(name="lock")
    @admin_check()
    @app_commands.describe(canvas="Canvas to lock")
    async def canvas_lock(self, interaction: Interaction, canvas: str):
        """Lock the canvas"""
        sql = await self.sql()
        try:
            canvas = await self.fetch_canvas_by_name(sql, canvas)
        except ValueError as e:
            await sql.close()
            return await interaction.response.send_message(str(e))

        await canvas.lock(sql)
        await sql.close()

        await interaction.response.send_message(f"Locked canvas '{canvas.name}'")

    @canvas_lock.autocomplete("canvas")
    async def canvas_lock_autocomplete_canvas(
        self, interaction: Interaction, current: str
    ):
        return await self.autocomplete_canvas(interaction, current)

    @admin_canvas_group.command(name="unlock")
    @admin_check()
    @app_commands.describe(canvas="Canvas to unlock")
    async def canvas_unlock(self, interaction: Interaction, canvas: str):
        """Unlock the canvas"""
        sql = await self.sql()
        try:
            canvas = await self.fetch_canvas_by_name(sql, canvas)
        except ValueError as e:
            await sql.close()
            return await interaction.response.send_message(str(e))

        await canvas.unlock(sql)
        await sql.close()

        await interaction.response.send_message(f"Unlocked canvas '{canvas.name}'")

    @canvas_unlock.autocomplete("canvas")
    async def canvas_unlock_autocomplete_canvas(
        self, interaction: Interaction, current: str
    ):
        return await self.autocomplete_canvas(interaction, current)

    @admin_canvas_group.command(name="refresh")
    @admin_check()
    @app_commands.describe(canvas="Canvas to refresh")
    async def canvas_refresh(self, interaction: Interaction, canvas: str):
        """Force refresh the cache"""
        await interaction.response.defer()
        canvas: Canvas = await self.fetch_canvas_by_name(await self.sql(), canvas)
        if canvas.id not in self.bot.cache:
            return await interaction.followup.send(
                f"Canvas '{canvas}' is not in the cache."
            )

        sql = await self.sql()
        msg = await interaction.followup.send(f"Refreshing cache for {canvas}...")
        await self.bot.cache[canvas.id].force_refresh(sql)
        await sql.close()
        await msg.edit(content=f"Refreshed cache for {canvas}.")

    @canvas_refresh.autocomplete("canvas")
    async def canvas_refresh_autocomplete_canvas(
        self, interaction: Interaction, current: str
    ):
        return await self.autocomplete_canvas(interaction, current)

    @admin_canvas_group.command(name="paste")
    @admin_check()
    @app_commands.describe(
        image="Image to paste",
        x="top-left x coordinate",
        y="top-left y coordinate",
    )
    async def canvas_paste(
        self, interaction: Interaction, image: Attachment, x: int, y: int
    ):
        """Paste an image onto the canvas"""
        sql = await self.sql()

        try:
            user, canvas = await self.find_canvas(interaction.user.id)
        except ValueError as e:
            await sql.close()
            return await interaction.response.send_message(str(e), ephemeral=True)

        await interaction.response.defer()

        if canvas.is_locked:
            await sql.close()
            return await interaction.followup.send(f"**{canvas.name}** is read-only.")

        canvas = await self.check_cache(canvas)

        pixels, size = await self.bot.loop.run_in_executor(
            None, self.paste_from_bytes, BytesIO(await image.read())
        )

        xy0 = Coordinates(x, y)
        xy1 = xy0 + size
        bbox = xy0.bbox_to(xy1)

        if bbox not in canvas:
            await sql.close()
            return await interaction.followup.send(f"Image is out of bounds. ({bbox})")

        final_pixels = []
        for pixel in pixels:
            pixel.xy += xy0
            final_pixels.append(pixel)

        await canvas.place_pixels(sql, user=user, pixels=final_pixels)

        await sql.close()

        await interaction.followup.send(f"Placed image at ({x}, {y}) on {canvas.name}.")

    def paste_from_bytes(self, img_bytes: BytesIO):
        colors = Palette(self.palette.get_all_event_colors(self.info.current_event_id))
        blank_rgb = (1, 1, 1)

        img = Image.open(img_bytes, "r")
        img = img.convert("RGBA")
        width, height = img.size
        pixel_values = numpy.array(list(img.getdata())).reshape((height, width, 4))

        pixels = []
        for row, i in enumerate(pixel_values):
            for col, pixel in enumerate(i):
                if pixel[3] == 0:
                    continue
                rgb = tuple(pixel[:3])
                if rgb == blank_rgb:
                    color = colors["blank"]
                else:
                    color = colors[rgb]
                if color is None:
                    raise ValueError(f"Invalid pixel color at ({col}, {row})")

                pixels.append(
                    Pixel(
                        xy=Coordinates(col, row),
                        color=color,
                    )
                )

        return pixels, (width, height)

    @admin_canvas_group.command(name="create")
    @admin_check()
    @app_commands.describe(
        name="Name of the canvas",
        width="Pixel width",
        height="Pixel height",
        event="Event ID",
        id="Canvas ID (leave blank to auto-generate)",
        cooldown_length="Cooldown length in seconds (default 30s)",
    )
    async def canvas_create(
        self,
        interaction: Interaction,
        name: str,
        width: int,
        height: int,
        event: int = None,
        id: int = None,
        cooldown_length: int = 30,
    ):
        """Create a new canvas"""
        await interaction.response.defer()

        canvas = Canvas(
            _id=id,
            name=name,
            width=width,
            height=height,
            event=Event(_id=event),
            cooldown_length=cooldown_length,
        )

        print(f"Creating canvas {canvas.name} ({canvas.width}x{canvas.height})")

        timer = Timer()

        sql = await self.sql()
        _id = await sql.insert_canvas(canvas)
        timer.mark("Inserted canvas")
        canvas.id = _id
        await sql.create_canvas_partition(canvas)
        timer.mark("Created canvas partition")
        await sql.create_pixels(canvas, self.palette.blank_color)
        timer.mark("Inserted blank pixels")
        await sql.close()

        await interaction.followup.send(
            f"Created canvas {canvas.name} ({canvas.width}x{canvas.height})."
        )

        self.bot.cache[canvas.id] = Cache(await self.sql(), canvas=canvas)

    @admin_canvas_group.command(name="edit")
    @admin_check()
    @app_commands.describe(
        canvas="Canvas to edit",
        name="New name",
        event="New event ID",
        cooldown_length="New cooldown length in seconds",
    )
    async def canvas_edit(
        self,
        interaction: Interaction,
        canvas: str,
        name: str = None,
        event: int = None,
        cooldown_length: int = None,
    ):
        """Edit a canvas"""
        await interaction.response.defer()

        sql = await self.sql()
        canvas = await self.fetch_canvas_by_name(sql, canvas)

        if name:
            canvas.name = name
        if event:
            canvas.event = Event(_id=event)
        if cooldown_length:
            canvas.cooldown_length = cooldown_length

        await canvas.edit(sql)
        await sql.close()

        await interaction.followup.send(f"Edited canvas '{canvas.name}'")

    @canvas_edit.autocomplete("canvas")
    async def canvas_edit_autocomplete_canvas(
        self, interaction: Interaction, current: str
    ):
        return await self.autocomplete_canvas(interaction, current)

    admin_blacklist_group = app_commands.Group(
        name="blacklist", description="Blacklist commands", parent=admin_group
    )

    @admin_blacklist_group.command(name="add")
    @admin_check()
    @app_commands.describe(user="User to blacklist")
    async def blacklist_add(self, interaction: Interaction, user: UserDiscord):
        """Blacklist a user"""
        await interaction.response.defer()
        sql = await self.sql()
        user_obj = await sql.fetch_user(user.id)
        if user_obj.is_blacklisted:
            await sql.close()
            return await interaction.followup.send(
                f"{user.mention} is already blacklisted."
            )
        await user_obj.add_blacklist(sql)
        await sql.close()
        await interaction.followup.send(f"Blacklisted {user.mention}.")

    @admin_blacklist_group.command(name="remove")
    @admin_check()
    @app_commands.describe(user="User to unblacklist")
    async def blacklist_remove(self, interaction: Interaction, user: UserDiscord):
        """Unblacklist a user"""
        await interaction.response.defer()
        sql = await self.sql()
        user_obj = await sql.fetch_user(user.id)
        if not user_obj.is_blacklisted:
            await sql.close()
            return await interaction.followup.send(
                f"{user.mention} is not blacklisted."
            )
        await user_obj.remove_blacklist(sql)
        await sql.close()
        await interaction.followup.send(f"Unblacklisted {user.mention}.")

    @admin_blacklist_group.command(name="view")
    @admin_check()
    async def blacklist_view(self, interaction: Interaction):
        """View the blacklist"""
        await interaction.response.defer()
        sql = await self.sql()
        blacklisted = await sql.fetch_blacklist()
        await sql.close()

        embed = self.base_embed(title="Blacklist")
        embed.description = "\n".join([f"- {user}" for user in blacklisted])
        if not blacklisted:
            embed.description = "No users blacklisted."
        await interaction.followup.send(embed=embed)

    admin_colors_group = app_commands.Group(
        name="colors", description="Color commands", parent=admin_group
    )

    @admin_colors_group.command(name="reload")
    @admin_check()
    async def colors_reload(self, interaction: Interaction):
        """Reload the colors"""
        await interaction.response.defer()
        sql = await self.sql()
        await self.load_colors()
        await sql.close()
        await interaction.followup.send("Reloaded colors.")

    @admin_colors_group.command(name="create")
    @admin_check()
    @app_commands.describe(
        name="Name of the color",
        code="Abbreviated code",
        hex="Hex code",
        r="Red value",
        g="Green value",
        b="Blue value",
        emoji="Emoji to use. Leave blank to generate new emoji.",
    )
    async def colors_create(
        self,
        interaction: Interaction,
        name: str,
        code: str,
        hex: str = None,
        r: int = None,
        g: int = None,
        b: int = None,
        emoji: str = None,
    ):
        """Create a new color"""
        if (hex is not None) == all(i is not None for i in [r, g, b]):
            return await interaction.response.send_message(
                "Please provide either a hex code or all of the RGB values."
            )

        if r and g and b:
            if not all([0 <= c <= 255 for c in [r, g, b]]):
                return await interaction.response.send_message(
                    "Invalid RGB values. Please provide values between 0 and 255."
                )
        elif hex:
            if len(hex) != 6:
                return await interaction.response.send_message(
                    "Invalid hex code. Please provide a 6-character hex code."
                )
            else:
                r, g, b = tuple(int(hex[i : i + 2], 16) for i in (0, 2, 4))

        await interaction.response.defer()

        color = Color(name=name, code=code, rgba=[r, g, b, 255], _global=False)

        if emoji is not None:
            if not re.match(r"<a?:\w+:(\d+)>$", emoji):
                return await interaction.followup.send("Invalid emoji.")
            else:
                emoji_id = int(re.match(r"<a?:\w+:(\d+)>", emoji).group(1))
                emoji_name = re.match(r"<a?:(\w+):\d+>", emoji).group(1)
                color.emoji_id = emoji_id
                color.emoji_name = emoji_name
        else:
            image_bytes, _ = await self.async_image_bytes(color.to_image_emoji)
            emoji = await self.info.current_emoji_server.create_custom_emoji(
                name=f"pl_{neutralise(color.code)}", image=image_bytes.read()
            )

            color.emoji_name = emoji.name
            color.emoji_id = emoji.id

        sql = await self.sql()
        while True:
            try:
                await sql.insert_color(color)
            except UniqueViolationError:
                pass
            else:
                break
        await sql.close()

        await interaction.followup.send(
            f"Created color {color.name} ({color.code}). {color.emoji_formatted}"
        )
        await self.load_colors()

    admin_register_group = app_commands.Group(
        name="register", description="Register commands", parent=admin_group
    )

    @admin_register_group.command(name="participation")
    @admin_check()
    @app_commands.describe(
        guild_id="ID of the guild to register",
        event_id="ID of the event to register for. Leave blank to use the current event.",
        color_code="Code of custom color. Must already exist.",
        invite="Invite link to the guild",
        manager_role_id="ID of the manager role",
    )
    async def register_participate(
        self,
        interaction: Interaction,
        guild_id: str,
        event_id: int = None,
        color_code: str = None,
        invite: str = None,
        manager_role_id: int = None,
    ):
        """Register a guild to participate"""
        if not guild_id.isdigit():
            return await interaction.response.send_message("Invalid guild ID.")
        else:
            guild_id = int(guild_id)
        if event_id is None:
            event_id = self.info.current_event_id

        await interaction.response.defer()
        from objects.guild import Guild

        sql = await self.sql()

        if color_code.isdigit():
            color = await sql.fetch_color_by_id(int(color_code))
        else:
            color = await sql.fetch_colors_by_code(color_code)
            color = color[color_code] if color else None
        if color is None:
            return await interaction.followup.send("Invalid color code.")

        if await sql.fetch_participation(guild_id, event_id):
            return await interaction.followup.send("Guild is already participating.")

        await sql.fetch_guild(
            guild_id,
            insert_on_fail=Guild(
                _id=guild_id, invite=invite, manager_role_id=manager_role_id
            ),
        )

        participation = Participation(
            guild_id=guild_id,
            event_id=event_id,
            color=color,
        )

        await sql.insert_participation(participation)

        await sql.close()

        await interaction.followup.send(f"Registered guild {guild_id} to participate.")

    @admin_register_group.command(name="edit-guild")
    @admin_check()
    @app_commands.describe(
        guild_id="ID of the guild to register/edit",
        invite="Invite link to the guild",
        manager_role_id="ID of the manager role",
    )
    async def register_guild(
        self,
        interaction: Interaction,
        guild_id: str,
        invite: str = None,
        manager_role_id: int = None,
    ):
        """Register a new guild / Edit an existing guild"""
        if not guild_id.isdigit():
            return await interaction.response.send_message("Invalid guild ID.")
        else:
            guild_id = int(guild_id)

        await interaction.response.defer()

        from objects.guild import Guild

        sql = await self.sql()

        guild = await sql.fetch_guild(
            guild_id,
            insert_on_fail=Guild(
                _id=guild_id, invite=invite, manager_role_id=manager_role_id
            ),
        )

        await sql.close()

        await interaction.followup.send(f"Registered/edited guild {guild.id}.")


# Imager stuff
# - Frames
# Other stuff
# - Frames
# - Setup - modular setup views that set up servers
#   - Start - set completely new values
#   - Edit - edit existing values
#   - View
#   - Values
#       - Manager role - (+ admin and manage server always have access)
#       - Color - select previous color or create new one (participation-only)
#       - Invite url - (participation-only)
# - Follow channel https://discordpy.readthedocs.io/en/stable/api.html?highlight=textchannel#discord.TextChannel.follow


async def setup(bot):
    await bot.add_cog(CanvasCog(bot))
