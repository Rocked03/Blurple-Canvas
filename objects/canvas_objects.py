from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator, Any

from PIL import Image, ImageDraw
from asyncpg import Connection
from discord import User as UserDiscord, Guild as GuildDiscord, Role, Client


class DiscordObject:
    def __init__(self, *, bot: Client = None, **kwargs):
        self.bot = bot

    def set_bot(self, bot: Client):
        self.bot = bot


class Canvas(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        name: str = None,
        locked: bool = None,
        event_id: int = None,
        width: int = None,
        height: int = None,
        event: Event = None,
        pixels: dict[tuple[int, int], Pixel] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name
        self.locked = locked
        self.event_id = event_id
        self.width = width
        self.height = height
        self.pixels = pixels

        self.event = (
            Event(_id=event_id, **kwargs)
            if event is None and event_id is not None
            else event
        )

    def is_locked(self):
        return self.locked

    def get_dimensions(self):
        return self.width, self.height

    async def place_pixel(
        self,
        sql_manager: SQLManager,
        *,
        user: User,
        guild_id: int = None,
        x: int,
        y: int,
        color: Color,
    ):
        pixel = Pixel(x=x, y=y, color=color, canvas=self)
        await sql_manager.update_pixel(pixel=pixel, user_id=user.id, guild_id=guild_id)

    async def get_frame(self, sql_manager: SQLManager, bbox: tuple[int, int, int, int]):
        frame = Frame(
            canvas_id=self.id,
            bbox=bbox,
        )
        await frame.load_pixels(sql_manager)
        return frame

    async def get_frame_from_coordinate(
        self, sql_manager: SQLManager, xy: tuple[int, int], zoom: int
    ):
        frame = Frame.from_coordinate(self, xy, zoom)
        await frame.load_pixels(sql_manager)
        return frame

    def __str__(self):
        return f"Canvas {self.name} ({self.id})"


class Pixel(DiscordObject):
    def __init__(
        self,
        *,
        canvas_id: int = None,
        x: int = None,
        y: int = None,
        color_id: int = None,
        color: Color = None,
        canvas: Canvas = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.x = x
        self.y = y

        self.canvas = (
            Canvas(_id=canvas_id, **kwargs)
            if canvas is None and canvas_id is not None
            else canvas
        )
        self.color = (
            Color(_id=color_id, **kwargs)
            if color is None and color_id is not None
            else color
        )

    def get_coordinates(self):
        return self.x, self.y

    def __str__(self):
        return f"({self.x}, {self.y})"


class Color(DiscordObject):
    def __init__(
        self,
        *,
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

        self.rgba: tuple[int, int, int, int] | None = (
            tuple(rgba[i] if len(rgba) > i else [0, 0, 0, 255][i] for i in range(4))
            if rgba
            else None
        )

    def emoji_formatted(self):
        return f"<:{self.emoji_name}:{self.emoji_id}>" if self.emoji_name else None

    def rgba_formatted(self):
        return f"rgba({', '.join(map(str, self.rgba))})" if self.rgba else None

    def __str__(self):
        return f"Color {self.name} {self.rgba_formatted()}"


class Frame(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        canvas_id: int = None,
        x_0: int = None,
        y_0: int = None,
        x_1: int = None,
        y_1: int = None,
        pixels: list[Pixel] = None,
        bbox: tuple[int, int, int, int] = None,
        canvas: Canvas = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.bbox: tuple[int, int, int, int] | None = (
            (x_0, x_1, y_0, y_1) if not bbox and (x_0 and x_1 and y_0 and y_1) else bbox
        )
        self.pixels = pixels

        self.size = (self.bbox[2] - self.bbox[0] + 1, self.bbox[3] - self.bbox[1] + 1)

        self.canvas = (
            Canvas(_id=canvas_id, **kwargs)
            if canvas is None and canvas_id is not None
            else canvas
        )

    @staticmethod
    def from_coordinate(canvas: Canvas, xy: tuple[int, int], zoom: int):
        (x, y) = xy
        return Frame(
            canvas=canvas,
            bbox=(
                min(max(x - (zoom // 2), 0), canvas.width - zoom),
                min(max(y - (zoom // 2), 0), canvas.height - zoom),
                max(min(x + (zoom // 2), canvas.width), zoom),
                max(min(y + (zoom // 2), canvas.height), zoom),
            ),
        )

    def bbox_formatted(self):
        return f"({self.bbox[0]}, {self.bbox[1]}) - ({self.bbox[2]}, {self.bbox[3]})"

    async def load_pixels(self, sql_manager: SQLManager):
        self.pixels = await sql_manager.fetch_pixels(self.canvas.id, self.bbox)

    def justified_pixels(self):
        if self.pixels is None:
            return []
        return {
            (pixel.x - self.bbox[0], pixel.y - self.bbox[1]): pixel
            for pixel in self.pixels
            if self.bbox[0] <= pixel.x <= self.bbox[2]
            and self.bbox[1] <= pixel.y <= self.bbox[3]
        }

    def generate_image(self, *, zoom: int = 1) -> Image.Image:
        img = Image.new("RGBA", self.multiply_zoom(zoom), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for coordinates, pixel in self.justified_pixels().items():
            adjusted_coordinates = (coordinates[0] * zoom, coordinates[1] * zoom)
            opposite_corner = (
                adjusted_coordinates[0] + zoom,
                adjusted_coordinates[1] + zoom,
            )
            draw.rectangle(
                (adjusted_coordinates, opposite_corner),
                pixel.color.rgba,
            )
        return img

    def multiply_zoom(self, zoom: int) -> tuple[int, int]:
        return tuple[int, int]([self.size[0] * zoom, self.size[1] * zoom])

    def __str__(self):
        return f"Frame {self.bbox_formatted()} ({self.canvas})"


class CustomFrame(Frame):
    def __init__(
        self, *, name: str = None, guild_id: int = None, guild: Guild = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name

        self.guild = (
            Guild(_id=guild_id, **kwargs)
            if guild is None and guild_id is not None
            else guild
        )

    def __str__(self):
        return f"Custom Frame {self.name} ({self.id}) ({self.canvas})"


class User(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        current_board: int = None,
        skip_confirm: bool = None,
        cooldown_remind: bool = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.current_board = current_board
        self.skip_confirm = skip_confirm
        self.cooldown_remind = cooldown_remind

        self.user: UserDiscord | None = None

    def set_user(self, user):
        self.user = user

    def load_user(self):
        if self.bot is None:
            raise ValueError("Bot not loaded")
        user = self.bot.get_user(self.id)
        if user is not None:
            self.set_user(user)
        else:
            raise ValueError(f"User with id {self.id} not found")

    async def set_current_board(self, sql_manager: SQLManager, board_id: int):
        self.current_board = board_id
        await sql_manager.set_current_board(self)

    async def toggle_skip_confirm(self, sql_manager: SQLManager):
        self.skip_confirm = not self.skip_confirm
        await sql_manager.set_skip_confirm(self)

    async def toggle_cooldown_remind(self, sql_manager: SQLManager):
        self.cooldown_remind = not self.cooldown_remind
        await sql_manager.set_cooldown_remind(self)

    async def place_pixel(
        self,
        sql_manager: SQLManager,
        *,
        canvas: Canvas,
        guild_id: int = None,
        x: int,
        y: int,
        color: Color,
    ):
        await canvas.place_pixel(
            sql_manager=sql_manager, user=self, guild_id=guild_id, x=x, y=y, color=color
        )

    def __str__(self):
        return f"User {self.id}"


class HistoryRecord(DiscordObject):
    def __init__(
        self,
        *,
        _id: int = None,
        canvas_id: int = None,
        user_id: int = None,
        x: int = None,
        y: int = None,
        color_id: int = None,
        timestamp: datetime = None,
        guild_id: int = None,
        user: User = None,
        pixel: Pixel = None,
        guild: Guild = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.id = _id
        self.timestamp = timestamp

        self.user = (
            User(_id=user_id, **kwargs)
            if user is None and user_id is not None
            else user
        )
        self.pixel = (
            Pixel(canvas_id=canvas_id, x=x, y=y, color_id=color_id, **kwargs)
            if pixel is None
            else pixel
        )
        self.guild = (
            Guild(_id=guild_id, **kwargs)
            if guild is None and guild_id is not None
            else guild
        )

    def __str__(self):
        return f"HistoryRecord {self.user.id} {self.pixel} ({self.timestamp})"


class Guild(DiscordObject):
    def __init__(self, *, _id: int = None, manager_role: int = None, **kwargs):
        super().__init__(**kwargs)
        self.id = _id
        self.manager_role_id = manager_role

        self.guild: GuildDiscord | None = None
        self.manager_role: Role | None = None

        if self.bot is not None:
            self.load_guild()
            if self.manager_role_id is not None:
                self.load_manager_role()

    def set_guild(self, guild: GuildDiscord):
        self.guild = guild

    def set_manager_role(self, role: Role):
        self.manager_role = role

    def load_guild(self):
        if self.bot is None:
            raise ValueError("Bot not loaded")
        guild = self.bot.get_guild(self.id)
        if guild is not None:
            self.set_guild(guild)
        else:
            raise ValueError(f"Guild with id {self.id} not found")

    def load_manager_role(self):
        if self.guild is None:
            raise ValueError("Guild not loaded")
        role = self.guild.get_role(self.manager_role_id)
        if role is not None:
            self.set_manager_role(role)
        else:
            raise ValueError(
                f"Role with id {self.manager_role_id} not found in guild {self.id}"
            )

    def __str__(self):
        return f"Guild {self.id}"


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


class Event(DiscordObject):
    def __init__(self, *, _id: int = None, name: str = None, **kwargs):
        super().__init__(**kwargs)
        self.id = _id
        self.name = name

    def __str__(self):
        return f"Event {self.name} ({self.id})"


class Participation(Guild):
    def __init__(
        self,
        *,
        guild_id: int = None,
        event_id: int = None,
        custom_color: bool = None,
        color_id: int = None,
        event: Event = None,
        color: Color = None,
        **kwargs,
    ):
        super().__init__(_id=guild_id, **kwargs)
        self.custom_color = custom_color

        self.event = (
            Event(_id=event_id, **kwargs)
            if event is None and event_id is not None
            else event
        )
        self.color = (
            Color(_id=color_id, **kwargs)
            if (color is None and color_id is not None) and custom_color
            else color
        )

    def has_custom_color(self):
        return self.custom_color

    def get_color_id(self):
        return self.color.id if self.custom_color and self.color else None

    def __str__(self):
        return f"Participation {self.id} {self.event.id}"


class SQLManager:
    def __init__(self, conn: Connection, bot: Client = None):
        self.conn = conn
        self.bot = bot

    async def fetch_canvas(self, canvas_id) -> Canvas:
        row = await self.conn.fetchrow("SELECT * FROM canvas WHERE id = $1", canvas_id)
        return Canvas(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_colors(
        self, *, color_ids: list[int] = None, color_codes: list[str] = None
    ) -> list[Color]:
        if color_ids:
            rows = await self.conn.fetch(
                "SELECT * FROM color WHERE id = ANY($1)", color_ids
            )
        elif color_codes:
            rows = await self.conn.fetch(
                "SELECT * FROM color WHERE code = ANY($1)", color_codes
            )
        else:
            rows = await self.conn.fetch("SELECT * FROM color")
        return [Color(bot=self.bot, **rename_invalid_keys(row)) for row in rows]

    async def fetch_color_by_id(self, color_id: int) -> Color:
        return (await self.fetch_colors(color_ids=[color_id]))[0]

    async def fetch_colors_by_code(self, color_code: str) -> list[Color]:
        return await self.fetch_colors(color_codes=[color_code])

    async def fetch_history_records(
        self, canvas_id: int, *, user_id: int = None
    ) -> Generator[HistoryRecord, Any, None]:
        if user_id:
            rows = await self.conn.fetch(
                "SELECT * FROM history WHERE canvas_id = $1 AND user_id = $2 ORDER BY timestamp",
                canvas_id,
                user_id,
            )
        else:
            rows = await self.conn.fetch(
                "SELECT * FROM history WHERE canvas_id = $1 ORDER BY timestamp",
                canvas_id,
            )
        return (HistoryRecord(bot=self.bot, **rename_invalid_keys(row)) for row in rows)

    async def fetch_participation(self, guild_id: int, event_id: int) -> Participation:
        row = await self.conn.fetchrow(
            (
                "SELECT p.*, g.id, c.code, c.name, c.emoji_name, c.emoji_id "
                "FROM participation p "
                "LEFT JOIN guild g ON p.guild_id = g.id "
                "LEFT JOIN public.color c ON c.id = p.color_id "
                "WHERE guild_id = $1 AND event_id = $2"
            ),
            guild_id,
            event_id,
        )
        return Participation(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_info(self) -> Info:
        row = await self.conn.fetchrow("SELECT * FROM info")
        return Info(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_pixels(
        self, canvas_id: int, bbox: tuple[int, int, int, int]
    ) -> list[Pixel]:
        pixels = await self.conn.fetch(
            (
                "SELECT p.x, p.y, p.color_id "
                "FROM pixels p "
                "WHERE canvas_id = $1 AND "
                "x >= $2 AND x <= $4 AND y >= $3 AND y <= $5"
            ),
            canvas_id,
            *bbox,
        )
        colors = {
            c["id"]: rename_invalid_keys(c)
            for c in await self.conn.fetch(
                "SELECT * FROM color WHERE id = ANY($1)",
                list(set(p["color_id"] for p in pixels)),
            )
        }
        for c in colors:
            colors[c].pop("_id")
        return [
            Pixel(
                bot=self.bot,
                **rename_invalid_keys(pixel),
                **colors[pixel["color_id"]],
            )
            for pixel in pixels
        ]

    async def fetch_user(self, user_id: int, *, insert_on_fail: User = None) -> User:
        row = await self.conn.fetchrow(
            "SELECT * FROM public.user WHERE id = $1", user_id
        )
        if row:
            return User(bot=self.bot, **rename_invalid_keys(row))
        elif insert_on_fail:
            await self.insert_user(insert_on_fail)
            return insert_on_fail
        else:
            return await self.insert_empty_user(user_id)

    async def insert_color(self, color: Color):
        await self.conn.execute(
            (
                "INSERT INTO color (id, code, emoji_name, emoji_id, global, name, rgba) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7)"
            ),
            color.code,
            color.emoji_name,
            color.emoji_id,
            color.is_global,
            color.name,
            color.rgba,
        )  # TODO: color ID auto increment?

    async def insert_participation(self, participation: Participation):
        await self.conn.execute(
            (
                "INSERT INTO participation (guild_id, event_id, custom_color, color_id) "
                "VALUES ($1, $2, $3, $4)"
            ),
            participation.guild.id,
            participation.event.id,
            participation.custom_color,
            participation.color.id,
        )

    async def insert_history_record(self, history_record: HistoryRecord):
        await self.conn.execute(
            (
                "INSERT INTO history (canvas_id, user_id, x, y, color_id, timestamp) "
                "VALUES ($1, $2, $3, $4, $5, $6)"
            ),
            history_record.pixel.canvas.id,
            history_record.user.id,
            history_record.pixel.x,
            history_record.pixel.y,
            history_record.pixel.color.id,
            history_record.timestamp,
        )

    async def insert_user(self, user: User):
        await self.conn.execute(
            (
                "INSERT INTO public.user (id, current_board, skip_confirm, cooldown_remind) "
                "VALUES ($1, $2, $3, $4)"
            ),
            user.id,
            user.current_board,
            user.skip_confirm,
            user.cooldown_remind,
        )

    async def insert_empty_user(self, user_id: int) -> User:
        user = User(
            id=user_id, current_board=None, skip_confirm=False, cooldown_remind=False
        )
        await self.insert_user(user)
        return user

    async def set_pixel(self, pixel: Pixel):
        await self.conn.execute(
            (
                "UPDATE pixels "
                "SET color_id = $1 "
                "WHERE canvas_id = $2 AND x = $3 AND y = $4"
            ),
            pixel.color.id,
            pixel.canvas.id,
            pixel.x,
            pixel.y,
        )

    async def update_pixel(
        self,
        *,
        pixel: Pixel,
        user_id: int,
        timestamp: datetime = datetime.now(tz=timezone.utc),
        guild_id: int = None,
    ):
        record = HistoryRecord(
            pixel=pixel, user_id=user_id, guild_id=guild_id, timestamp=timestamp
        )
        await self.insert_history_record(record)
        await self.set_pixel(pixel)

    async def set_current_board(self, user: User):
        await self.fetch_user(user.id, insert_on_fail=user)
        await self.conn.execute(
            "UPDATE public.user SET current_board = $1 WHERE id = $2",
            user.current_board,
            user.id,
        )

    async def set_skip_confirm(self, user: User):
        await self.fetch_user(user.id, insert_on_fail=user)
        await self.conn.execute(
            "UPDATE public.user SET skip_confirm = $1 WHERE id = $2",
            user.skip_confirm,
            user.id,
        )

    async def set_cooldown_remind(self, user: User):
        await self.fetch_user(user.id, insert_on_fail=user)
        await self.conn.execute(
            "UPDATE public.user SET cooldown_remind = $1 WHERE id = $2",
            user.cooldown_remind,
            user.id,
        )


def rename_invalid_keys(data: dict) -> dict:
    renames = {
        "id": "_id",
        "global": "_global",
    }
    return {renames.get(k, k) if k in renames else k: v for k, v in data.items()}
