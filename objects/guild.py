from discord import Role, Guild as GuildDiscord

from objects.discordObject import DiscordObject


class Guild(DiscordObject):
    def __init__(self, _id: int = None, manager_role: int = None, **kwargs):
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
