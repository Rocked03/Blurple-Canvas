from objects.color import Color
from objects.discordObject import DiscordObject
from objects.event import Event
from objects.guild import Guild


class Participation(DiscordObject):
    def __init__(
        self,
        guild_id: int = None,
        event_id: int = None,
        custom_color: bool = None,
        color_id: int = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.custom_color = custom_color

        self.guild = Guild(_id=guild_id, **kwargs) if guild_id else None
        self.event = Event(_id=event_id, **kwargs) if event_id else None
        self.color = (
            Color(_id=color_id, **kwargs) if color_id and custom_color else None
        )

    def has_custom_color(self):
        return self.custom_color

    def get_color_id(self):
        return self.color.id if self.custom_color and self.color else None

    def __str__(self):
        return f"Participation {self.guild.id} {self.event.id}"
