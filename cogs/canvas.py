from discord import app_commands, Interaction, User
from discord.ext import commands


class CanvasCog(commands.Cog, name="Canvas"):
    """Canvas Module"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="view")
    async def view(
        self, interaction: Interaction, x: int = None, y: int = None, zoom: int = None
    ):
        """View the canvas"""
        pass

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
    async def stats(self, interaction: Interaction, user: User = None):
        """View user stats"""
        pass
