from objects.discordObject import DiscordObject
from objects.event import Event


class Canvas(DiscordObject):
    def __init__(
        self,
        _id: int = None,
        name: str = None,
        locked: bool = None,
        event_id: int = None,
        width: int = None,
        height: int = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.locked = locked
        self.event_id = event_id
        self.width = width
        self.height = height

        self.event = Event(_id=event_id, **kwargs) if event_id else None

    def is_locked(self):
        return self.locked

    def __str__(self):
        return f"Canvas {self.name} ({self.id})"
