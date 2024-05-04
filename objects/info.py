from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from discord import Guild, Interaction, Role, NotFound

from objects.discordObject import DiscordObject

if TYPE_CHECKING:
    from objects.event import Event


class Info(DiscordObject):
    def __init__(
        self,
        *,
        title: str = None,
        current_event_id: int = None,
        canvas_admin: list[int] = None,
        current_event: Event = None,
        cached_canvas_ids: list[int] = None,
        highlight_color: int = None,
        admin_server_id: int = None,
        admin_server: Guild = None,
        current_emoji_server_id: int = None,
        current_emoji_server: Guild = None,
        host_server_id: int = None,
        host_server: Guild = None,
        event_role_id: int = None,
        event_role: Role = None,
        default_canvas_id: int = None,
        all_colors_global: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.title = title
        self.canvas_admin_ids = canvas_admin
        self.cached_canvas_ids = cached_canvas_ids
        self.highlight_color = highlight_color
        self.default_canvas_id = default_canvas_id
        self.all_colors_global = all_colors_global
        self.admin_server_id = admin_server_id
        self.current_emoji_server_id = current_emoji_server_id
        self.event_role_id = event_role_id
        self.host_server_id = host_server_id

        from objects.event import Event

        self.current_event: Optional[Event] = (
            Event(_id=current_event_id, **kwargs)
            if not current_event and current_event_id
            else current_event
        )

        self.admin_server: Optional[Guild] = admin_server
        self.canvas_admin_roles: list[Role] = []
        self.current_emoji_server: Optional[Guild] = current_emoji_server
        self.host_server: Optional[Guild] = host_server
        self.event_role: Optional[Role] = event_role

        if self.bot:
            self.bot.loop.create_task(self.fetch_admin_server())
            self.bot.loop.create_task(self.fetch_host_server())
            self.bot.loop.create_task(self.fetch_current_emoji_server())

    @property
    def current_event_id(self):
        return self.current_event.id if self.current_event else None

    async def fetch_admin_server(self):
        try:
            if not self.admin_server:
                self.admin_server = await self.bot.fetch_guild(self.admin_server_id)
            if not self.canvas_admin_roles:
                self.canvas_admin_roles = [
                    self.admin_server.get_role(role_id)
                    for role_id in self.canvas_admin_ids
                ]
        except NotFound:
            pass
        return self.admin_server

    async def fetch_host_server(self):
        try:
            if not self.host_server:
                self.host_server = await self.bot.fetch_guild(self.host_server_id)
            if not self.event_role:
                self.event_role = self.host_server.get_role(self.event_role_id)
        except NotFound:
            pass
        return self.host_server

    async def fetch_current_emoji_server(self):
        try:
            if not self.current_emoji_server:
                self.current_emoji_server = await self.bot.fetch_guild(
                    self.current_emoji_server_id
                )
        except NotFound:
            pass
        return self.current_emoji_server

    async def check_perms(self, interaction: Interaction):
        try:
            member = await self.admin_server.fetch_member(interaction.user.id)
            if member is None:
                return False
            return any(role in member.roles for role in self.canvas_admin_roles)
        except NotFound:
            return False

    def __str__(self):
        return f"Info {self.current_event_id}"
