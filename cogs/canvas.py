import asyncio
import re
from functools import partial
from io import BytesIO
from typing import Optional, Callable

from PIL.Image import Image
from asyncpg import create_pool, Pool
from discord import (
    app_commands,
    Interaction,
    User as UserDiscord,
    Client,
    File,
    Embed,
    Message,
)
from discord.app_commands import Choice
from discord.ext import commands
from discord.utils import utcnow

from config import POSTGRES_CREDENTIALS
from objects.cache import Cache
from objects.canvas import Canvas
from objects.color import Palette, Color
from objects.coordinates import Coordinates
from objects.info import Info
from objects.sqlManager import SQLManager
from objects.timer import Timer
from objects.user import User
from objects.views import (
    ConfirmEnum,
    NavigationEnum,
    NavigateView,
    PaletteView,
    ConfirmView,
)


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

    async def autocomplete_color(
        self, interaction, current, colors: list[Color] = None
    ):
        return [
            Choice(name=color.name, value=str(color.id))
            for color in (colors if colors else self.palette.sorted())
            if neutralise(current) in neutralise(color.name)
            or neutralise(current) in neutralise(color.code)
            or current.isdigit()
            and color.id == int(current)
        ][:25]

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
        await interaction.response.defer()
        sql = await self.sql()

        timer = Timer()

        try:
            user, canvas = await self.find_canvas(interaction.user.id)
        except ValueError as e:
            await sql.close()
            return await interaction.followup.send(str(e), ephemeral=True)

        if user.is_blacklisted:
            await sql.close()
            return await interaction.followup.send(
                "You are blacklisted.", ephemeral=True
            )

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

        # 7 is max emoji limit
        frame = await canvas.get_frame_from_coordinate(sql, coordinates, 7, focus=True)

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

        if not user.skip_confirm or not color:
            old_view: Optional[ConfirmView] = None
            if not user.skip_confirm:
                # Navigating pixels
                while True:
                    embed.title = f"Place pixel • {canvas.name} {coordinates}"
                    embed.description = frame.to_emoji(
                        focus=self.palette.edit_color, new_color=color
                    )

                    view = NavigateView(
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
                            embed.title = f"Timed out • {canvas.name} {coordinates}"
                        elif view.confirm == ConfirmEnum.CANCEL:
                            embed.title = f"Cancelled • {canvas.name} {coordinates}"
                        await send_msg(msg, embed=embed, view=None)
                        await view.defer()
                        await user.clear_cooldown(sql)
                        await sql.close()
                        return

                    elif view.confirm == ConfirmEnum.CONFIRM:
                        old_view = view
                        break

                    else:
                        coordinates += view.direction.value
                        frame = await canvas.get_frame_from_coordinate(
                            sql, coordinates, 7, focus=True
                        )
                        old_view = view

            if not color:
                # Selecting color
                embed.title = f"Select color • {canvas.name} {coordinates}"
                embed.description = frame.to_emoji(focus=self.palette.edit_color)

                view = PaletteView(
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
                        embed.title = f"Timed out • {canvas.name} {coordinates}"
                    elif view.confirm == ConfirmEnum.CANCEL:
                        embed.title = f"Cancelled • {canvas.name} {coordinates}"
                    elif not view.dropdown.values:
                        embed.title = f"No color selected • {canvas.name} {coordinates}"
                    await send_msg(msg, embed=embed, view=None)
                    await view.defer()
                    await user.clear_cooldown(sql)
                    await sql.close()
                    return

                color = self.palette[view.dropdown.values[0]]

        # Place pixel
        await canvas.place_pixel(
            sql, user=user, xy=coordinates, color=color, guild_id=interaction.guild_id
        )
        frame = await canvas.regenerate_frame(sql, frame)
        embed.title = f"Placed pixel • {canvas.name} {coordinates}"
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
                    f"{color.guild.guild.name}"
                    if color.guild.guild
                    else "its own partner server"
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
    async def palette_autocomplete_palette(
        self, interaction: Interaction, current: str
    ):
        return [
            Choice(name="All", value="all"),
            Choice(name="Global", value="global"),
            Choice(name="Partner", value="guild"),
        ]

    @palette.autocomplete("color")
    async def palette_autocomplete_color(self, interaction: Interaction, current: str):
        return self.autocomplete_color(interaction, current)

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

    @app_commands.command(name="stats")
    async def stats(self, interaction: Interaction, user: UserDiscord = None):
        """View user stats"""
        # TODO: Implement
        # - me
        # - guild
        # - leaderboard
        pass

    # Admin Commands

    admin_group = app_commands.Group(name="admin", description="Admin commands")

    admin_canvas_group = app_commands.Group(
        name="canvas", description="Canvas commands", parent=admin_group
    )

    @admin_canvas_group.command(name="lock")
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

    @admin_canvas_group.command(name="create")
    async def canvas_create(self, interaction: Interaction, name: str):
        """Create a new canvas"""
        # TODO: Implement
        pass

    admin_blacklist_group = app_commands.Group(
        name="blacklist", description="Blacklist commands", parent=admin_group
    )

    @admin_blacklist_group.command(name="add")
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


# Admin commands
# - PERMS!!
# - Partner stuff + colour stuff
# - Create canvas
# - Paste
# Imager stuff
# - Frames
# Other stuff
# - Cooldown reminder


async def setup(bot):
    await bot.add_cog(CanvasCog(bot))
