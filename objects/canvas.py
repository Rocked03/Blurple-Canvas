from objects.discordObject import DiscordObject
from objects.event import Event


class Canvas(DiscordObject):
    def __init__(
        self,
        _id: int = None,
        name: str = None,
        locked: bool = None,
        eventId: int = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.locked = locked
        self.event_id = eventId

        self.event = Event(_id=eventId, **kwargs) if eventId else None

    def is_locked(self):
        return self.locked
