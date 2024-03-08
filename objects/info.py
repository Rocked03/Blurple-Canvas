from objects.discordObject import DiscordObject
from objects.event import Event


class Info(DiscordObject):
    def __init__(
        self, currentEvent: int = None, canvasAdmin: list[int] = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.current_event_id = currentEvent
        self.canvas_admin = canvasAdmin

        self.current_event = Event(_id=currentEvent, **kwargs)
