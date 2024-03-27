from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from discord import Guild, Interaction, Role

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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.title = title
        self.canvas_admin_ids = canvas_admin
        self.cached_canvas_ids = cached_canvas_ids
        self.highlight_color = highlight_color
        self.default_canvas_id = default_canvas_id

        from objects.event import Event

        self.current_event: Optional[Event] = (
            Event(_id=current_event_id, **kwargs)
            if not current_event and current_event_id
            else current_event
        )

        self.admin_server: Optional[Guild] = (
            self.bot.get_guild(admin_server_id)
            if admin_server_id and self.bot
            else admin_server
        )

        self.host_server: Optional[Guild] = (
            self.bot.get_guild(host_server_id)
            if host_server_id and self.bot
            else host_server
        )

        self.event_role: Optional[Role] = (
            self.host_server.get_role(event_role_id)
            if event_role_id and self.host_server
            else event_role
        )

        self.current_emoji_server: Optional[Guild] = (
            self.bot.get_guild(current_emoji_server_id)
            if current_emoji_server_id and self.bot
            else current_emoji_server
        )

        self.canvas_admin_roles = (
            [self.admin_server.get_role(role_id) for role_id in self.canvas_admin_ids]
            if self.admin_server
            else []
        )

    @property
    def current_event_id(self):
        return self.current_event.id if self.current_event else None

    async def check_perms(self, interaction: Interaction):
        member = await self.admin_server.fetch_member(interaction.user.id)
        if member is None:
            return False
        return any(role in member.roles for role in self.canvas_admin_roles)

    def __str__(self):
        return f"Info {self.current_event_id}"
