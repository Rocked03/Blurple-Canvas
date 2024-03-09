from objects.frame import Frame
from objects.guild import Guild


class CustomFrame(Frame):
    def __init__(
        self, *, name: str = None, guild_id: int = None, guild: Guild = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name

        self.guild = Guild(_id=guild_id, **kwargs) if not guild and guild_id else guild

    def __str__(self):
        return f"Custom Frame {self.name} ({self.id}) ({self.canvas})"
