import asyncio
from typing import Optional

from discord import User as UserDiscord

from objects.color import Color
from objects.discordObject import DiscordObject


class StatsBase(DiscordObject):
    def __init__(self, canvas_id: int = None, **kwargs):
        super().__init__(**kwargs)
        self.canvas_id = canvas_id


class UserStatsBase(StatsBase):
    def __init__(self, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id

        self.user: Optional[UserDiscord] = None

        if self.bot is not None:
            asyncio.run(self.load_user())

    @property
    def name(self):
        return str(self.user) if self.user else str(self.user_id)

    def set_user(self, user: UserDiscord):
        self.user = user

    async def load_user(self):
        if self.bot is None:
            raise ValueError("Bot not loaded")
        user = await self.bot.fetch_user(self.user_id)
        if user is not None:
            self.set_user(user)


class GuildStatsBase(StatsBase):
    def __init__(self, guild_id: int, **kwargs):
        super().__init__(**kwargs)
        self.guild_id = guild_id

        self.guild = None

        if self.bot is not None:
            asyncio.run(self.load_guild())

    @property
    def name(self):
        return self.guild.name if self.guild else str(self.guild_id)

    def set_guild(self, guild):
        self.guild = guild

    async def load_guild(self):
        if self.bot is None:
            raise ValueError("Bot not loaded")
        guild = await self.bot.fetch_guild(self.guild_id)
        if guild is not None:
            self.set_guild(guild)


class Ranking(UserStatsBase):
    def __init__(self, rank: int, total_pixels: int, **kwargs):
        super().__init__(**kwargs)
        self.ranking = rank
        self.total_pixels = total_pixels

    def __str__(self):
        return f"{self.ranking}. {self.name} - {self.total_pixels} pixels"

    def __gt__(self, other):
        return self.ranking > other.ranking

    def __lt__(self, other):
        return self.ranking < other.ranking

    def __eq__(self, other):
        return self.ranking == other.ranking


class MostFrequentColorStat:
    def __init__(self, most_frequent_color_id: int, color_count: int, **kwargs):
        super().__init__(**kwargs)
        self.color_count = color_count

        self.most_frequent_color: Color = Color(_id=most_frequent_color_id, **kwargs)

    def __str__(self):
        return f"{self.most_frequent_color} - {self.color_count} pixels"


class UserStats(Ranking, MostFrequentColorStat):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __str__(self):
        return f"User Stats - {self.name}"


class GuildStats(MostFrequentColorStat, GuildStatsBase):
    def __init__(self, total_pixels: int, **kwargs):
        super().__init__(**kwargs)
        self.total_pixels = total_pixels

    def __str__(self):
        return f"Guild Stats - {self.name}"
