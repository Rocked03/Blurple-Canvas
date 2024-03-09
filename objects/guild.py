from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Guild as GuildDiscord, Role

from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.color import Color
    from objects.event import Event


class Guild(DiscordObject):
    def __init__(self, *, _id: int = None, manager_role: int = None, **kwargs):
        super().__init__(**kwargs)
        self.id = _id
        self.manager_role_id = manager_role

        self.guild: GuildDiscord | None = None
        self.manager_role: Role | None = None

        if self.bot is not None:
            self.load_guild()
            if self.manager_role_id is not None:
                self.load_manager_role()

    def set_guild(self, guild: GuildDiscord):
        self.guild = guild

    def set_manager_role(self, role: Role):
        self.manager_role = role

    def load_guild(self):
        if self.bot is None:
            raise ValueError("Bot not loaded")
        guild = self.bot.get_guild(self.id)
        if guild is not None:
            self.set_guild(guild)
        else:
            raise ValueError(f"Guild with id {self.id} not found")

    def load_manager_role(self):
        if self.guild is None:
            raise ValueError("Guild not loaded")
        role = self.guild.get_role(self.manager_role_id)
        if role is not None:
            self.set_manager_role(role)
        else:
            raise ValueError(
                f"Role with id {self.manager_role_id} not found in guild {self.id}"
            )

    def __str__(self):
        return f"Guild {self.id}"


class Participation(Guild):
    def __init__(
        self,
        *,
        guild_id: int = None,
        event_id: int = None,
        custom_color: bool = None,
        color_id: int = None,
        event: Event = None,
        color: Color = None,
        **kwargs,
    ):
        super().__init__(_id=guild_id, **kwargs)
        self.custom_color = custom_color

        from objects.event import Event
        from objects.color import Color

        self.event = (
            Event(_id=event_id, **kwargs)
            if event is None and event_id is not None
            else event
        )
        self.color = (
            Color(_id=color_id, **kwargs)
            if (color is None and color_id is not None) and custom_color
            else color
        )

    def has_custom_color(self):
        return self.custom_color

    def get_color_id(self):
        return self.color.id if self.custom_color and self.color else None

    def __str__(self):
        return f"Participation {self.id} {self.event.id}"
