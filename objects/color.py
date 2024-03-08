from objects.discordObject import DiscordObject


class Color(DiscordObject):
    def __init__(
        self,
        _id: int = None,
        hex: str = None,
        code: str = None,
        emojiName: str = None,
        emojiId: int = None,
        _global: bool = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.hex = hex
        self.code = code
        self.emoji_name = emojiName
        self.emoji_id = emojiId
        self.is_global = _global

    def emoji_format(self):
        return f"<:{self.emoji_name}:{self.emoji_id}>"
