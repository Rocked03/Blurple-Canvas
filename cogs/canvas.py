from typing import Optional, Callable

from asyncpg import connect, Connection
from discord import app_commands, Interaction, User as UserDiscord, Client, File, Embed
from discord.ext import commands
from discord.utils import utcnow

from config import POSTGRES_CREDENTIALS
from objects.canvas import Canvas
from objects.sqlManager import SQLManager
from objects.user import User


class CanvasCog(commands.Cog, name="Canvas"):
    """Canvas Module"""

    def __init__(self, bot):
        self.bot: Client = bot

        # SQL
        self.conn: Optional[Connection] = None
        self.sql: Optional[SQLManager] = None
        self.bot.loop.create_task(self.startup_connect_sql())

    async def startup_connect_sql(self):
        self.conn = await connect(POSTGRES_CREDENTIALS)
        self.sql = SQLManager(self.conn)

    async def find_board(self, user_id) -> tuple[User, Canvas]:
        user = await self.sql.fetch_user(user_id)
        if user.current_canvas_id is None:
            raise ValueError(
                "You have not joined a board! Please use `/join` to join a board."
            )
        canvas = await self.sql.fetch_canvas(user.current_canvas_id)
        if canvas is None:
            raise ValueError("Cannot find your board. Please `/join` a board.")
        return user, canvas

    async def async_image(
        self, function: Callable, *args, file_name: str
    ) -> tuple[File, str]:
        image = await self.bot.loop.run_in_executor(None, function, *args)
        file = File(image, filename=file_name)
        return file, f"attachment://{file_name}"

    def base_embed(self, user: UserDiscord = None):
        embed = Embed(timestamp=utcnow())
        embed.set_footer(
            text=f"{str(user) + ' | ' if user else ''}" f"{self.bot.user.name}",
            icon_url=self.bot.user.avatar,
        )
        return embed

    @app_commands.command(name="view")
    async def view(
        self, interaction: Interaction, x: int = None, y: int = None, zoom: int = 25
    ):
        """View the canvas"""
        if (x is None) != (y is None):
            return await interaction.response().send_message(
                "Please provide both x and y coordinates."
            )

        try:
            user, canvas = await self.find_board(interaction.user.id)

            # Get frame
            if x is None and y is None:
                frame = await canvas.get_frame_full(self.sql)
            else:
                frame = await canvas.get_frame_from_coordinate(self.sql, (x, y), zoom)

        except ValueError as e:
            return await interaction.response().send_message(str(e), ephemeral=True)

        # Generate image
        file, file_name = await self.async_image(
            frame.generate_image,
            10,
            file_name=f"canvas_{canvas.name_safe()}_({x}-{y}).png",
        )

        # Embed
        embed = self.base_embed(interaction.user)
        embed.set_image(url=file_name)
        await interaction.response().send_message(embed=embed, file=file)

    @app_commands.command(name="place")
    async def place(self, interaction: Interaction, x: int, y: int, color: str = None):
        """Place a pixel on the canvas"""
        pass

    @app_commands.command(name="join")
    async def join(self, interaction: Interaction, board: str):
        """Join the canvas"""
        pass

    @app_commands.command(name="palette")
    async def palette(self, interaction: Interaction, color: str = None):
        """View the palette"""
        pass

    @app_commands.command(name="toggle-skip")
    async def toggle_skip(self, interaction: Interaction):
        """Toggle skip confirm"""
        pass

    @app_commands.command(name="toggle-remind")
    async def toggle_remind(self, interaction: Interaction):
        """Toggle cooldown remind"""
        pass

    @app_commands.command(name="stats")
    async def stats(self, interaction: Interaction, user: UserDiscord = None):
        """View user stats"""
        pass
