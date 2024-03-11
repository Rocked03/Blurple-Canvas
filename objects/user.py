from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Optional

from discord import User as UserDiscord

from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.canvas import Canvas
    from objects.color import Color
    from objects.sqlManager import SQLManager


class User(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        current_canvas_id: int = None,
        skip_confirm: bool = None,
        cooldown_remind: bool = None,
        blacklist: Blacklist = None,
        current_canvas: Canvas = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.skip_confirm = skip_confirm
        self.cooldown_remind = cooldown_remind

        self.user: Optional[UserDiscord] = None

        from objects.canvas import Canvas

        self.blacklist: Optional[Blacklist] = (
            Blacklist(user_id=self.id, **kwargs) if blacklist is None else None
        )
        self.current_canvas: Optional[Canvas] = (
            Canvas(_id=current_canvas_id, **kwargs)
            if current_canvas_id
            else current_canvas
        )

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

    def is_blacklisted(self):
        return self.blacklist.is_blacklisted()

    async def set_current_canvas(self, sql_manager: SQLManager, canvas: Canvas):
        if canvas.id is None:
            raise ValueError("No Canvas ID provided")
        self.current_canvas = canvas
        await sql_manager.set_current_canvas(self)

    async def toggle_skip_confirm(self, sql_manager: SQLManager):
        self.skip_confirm = not self.skip_confirm
        await sql_manager.set_skip_confirm(self)

    async def toggle_cooldown_remind(self, sql_manager: SQLManager):
        self.cooldown_remind = not self.cooldown_remind
        await sql_manager.set_cooldown_remind(self)

    async def place_pixel(
        self,
        sql_manager: SQLManager,
        *,
        canvas: Canvas,
        guild_id: int = None,
        x: int,
        y: int,
        color: Color,
    ):
        await canvas.place_pixel(
            sql_manager=sql_manager, user=self, guild_id=guild_id, x=x, y=y, color=color
        )

    async def get_cooldown(self, sql_manager: SQLManager) -> Cooldown:
        return await sql_manager.fetch_cooldown(self.id)

    async def hit_cooldown(self, sql_manager: SQLManager, cooldown_length: int):
        cooldown = await self.get_cooldown(sql_manager)
        if cooldown:
            if not cooldown.is_expired():
                return False

        new_cooldown = Cooldown(
            user_id=self.id,
            cooldown_time=datetime.now(tz=timezone.utc)
            + timedelta(seconds=cooldown_length),
        )
        if cooldown is None:
            await sql_manager.add_cooldown(new_cooldown)
        elif cooldown.cooldown_time is not None:
            await sql_manager.set_cooldown(new_cooldown)
        return True

    async def clear_cooldown(self, sql_manager: SQLManager):
        await sql_manager.clear_cooldown(self.id)

    async def add_blacklist(self, sql_manager: SQLManager):
        await sql_manager.add_blacklist(self.id)

    async def remove_blacklist(self, sql_manager: SQLManager):
        await sql_manager.remove_blacklist(self.id)

    def __str__(self):
        return f"User {self.id}"


class Blacklist(DiscordObject):
    def __init__(self, *, user_id: int, date_added: datetime = None, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.date_added = date_added

    def is_blacklisted(self):
        return self.date_added is not None


class Cooldown(DiscordObject):
    def __init__(
        self, *, user_id: int, cooldown_time: datetime, user: User = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.cooldown_time = cooldown_time
        self.user: User = User(_id=user_id, **kwargs) if user is None else user

    def is_expired(self):
        return (
            self.cooldown_time <= datetime.now(tz=timezone.utc)
            if self.cooldown_time
            else True
        )