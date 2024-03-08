from objects.discordObject import DiscordObject


class Event(DiscordObject):
    def __init__(self, _id: int = None, name: str = None, **kwargs):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
