from __future__ import annotations

from discord import Client


class DiscordObject:
    def __init__(self, *, bot: Client = None, **kwargs):
        self.bot = bot

    def set_bot(self, bot: Client):
        self.bot = bot
