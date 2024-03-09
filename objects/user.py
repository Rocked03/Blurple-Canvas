from discord import User as UserDiscord

from objects.discordObject import DiscordObject
from postgresql.postgresql_manager import SQLManager


class User(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        current_board: int = None,
        skip_confirm: bool = None,
        cooldown_remind: bool = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.current_board = current_board
        self.skip_confirm = skip_confirm
        self.cooldown_remind = cooldown_remind

        self.user: UserDiscord | None = None

    def set_user(self, user):
        self.user = user

    def load_user(self):
        if self.bot is None:
            raise ValueError("Bot not loaded")
        user = self.bot.get_user(self.id)
        if user is not None:
            self.set_user(user)
        else:
            raise ValueError(f"User with id {self.id} not found")

    async def set_current_board(self, sql_manager: SQLManager, board_id: int):
        self.current_board = board_id
        await sql_manager.set_current_board(self)

    async def toggle_skip_confirm(self, sql_manager: SQLManager):
        self.skip_confirm = not self.skip_confirm
        await sql_manager.set_skip_confirm(self)

    async def toggle_cooldown_remind(self, sql_manager: SQLManager):
        self.cooldown_remind = not self.cooldown_remind
        await sql_manager.set_cooldown_remind(self)

    def __str__(self):
        return f"User {self.id}"
