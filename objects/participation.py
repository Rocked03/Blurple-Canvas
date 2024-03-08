from objects.discordObject import DiscordObject
from objects.event import Event
from objects.guild import Guild


class Participation(DiscordObject):
    def __init__(
        self,
        guildId: int = None,
        eventId: int = None,
        customColor: bool = None,
        colorId: int = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.guild_id = guildId
        self.event_id = eventId
        self.custom_color = customColor
        self.color_id = colorId

        self.guild = Guild(_id=guildId, **kwargs) if guildId else None
        self.event = Event(_id=eventId, **kwargs) if eventId else None

    def has_custom_color(self):
        return self.custom_color

    def get_color_id(self):
        return self.color_id if self.custom_color else None
