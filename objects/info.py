from objects.discordObject import DiscordObject
from objects.event import Event


class Info(DiscordObject):
    def __init__(
        self,
        *,
        current_event_id: int = None,
        canvas_admin: list[int] = None,
        current_event: Event = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.current_event_id = current_event_id
        self.canvas_admin = canvas_admin

        self.current_event = (
            Event(_id=current_event_id, **kwargs)
            if not current_event and current_event_id
            else current_event
        )

    def __str__(self):
        return f"Info {self.current_event_id}"
