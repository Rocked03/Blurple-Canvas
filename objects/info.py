from __future__ import annotations

from typing import TYPE_CHECKING, Optional

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
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.title = title
        self.current_event_id = current_event_id
        self.canvas_admin = canvas_admin
        self.cached_canvas_ids = cached_canvas_ids
        self.highlight_color = highlight_color

        from objects.event import Event

        self.current_event: Optional[Event] = (
            Event(_id=current_event_id, **kwargs)
            if not current_event and current_event_id
            else current_event
        )

    def __str__(self):
        return f"Info {self.current_event_id}"
