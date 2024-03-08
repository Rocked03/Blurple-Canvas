from objects.discordObject import DiscordObject


class Color(DiscordObject):
    def __init__(
        self,
        _id: int = None,
        name: str = None,
        code: str = None,
        emoji_name: str = None,
        emoji_id: int = None,
        _global: bool = None,
        rgba: list[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.code = code
        self.emoji_name = emoji_name
        self.emoji_id = emoji_id
        self.is_global = _global

        self.rgba = (
            [rgba[i] if len(rgba) > i else [0, 0, 0, 255][i] for i in range(4)]
            if rgba
            else None
        )

    def emoji_format(self):
        return f"<:{self.emoji_name}:{self.emoji_id}>" if self.emoji_name else None

    def rgba_format(self):
        return f"rgba({', '.join(map(str, self.rgba))})" if self.rgba else None

    def __str__(self):
        return f"Color {self.name} {self.rgba_format()}"
