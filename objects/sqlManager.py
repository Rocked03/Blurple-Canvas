from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator, Any
from typing import TYPE_CHECKING

from asyncpg import Connection
from discord import Client

if TYPE_CHECKING:
    from objects.canvas import Canvas
    from objects.color import Color
    from objects.guild import Participation
    from objects.historyRecord import HistoryRecord
    from objects.info import Info
    from objects.pixel import Pixel
    from objects.user import User, Cooldown


class SQLManager:
    def __init__(self, conn: Connection, bot: Client = None):
        self.conn = conn
        self.bot = bot

    async def fetch_canvas(self, canvas_id) -> Canvas:
        row = await self.conn.fetchrow("SELECT * FROM canvas WHERE id = $1", canvas_id)
        from objects.canvas import Canvas

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

        from objects.color import Color

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

        from objects.historyRecord import HistoryRecord

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

        from objects.guild import Participation

        return Participation(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_info(self) -> Info:
        row = await self.conn.fetchrow("SELECT * FROM info")
        from objects.info import Info

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

        from objects.pixel import Pixel

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
            "SELECT u.*, b.date_added "
            "FROM public.user u "
            "LEFT JOIN blacklist b ON u.id = b.user_id "
            "WHERE id = $1",
            user_id,
        )
        if row:
            from objects.user import User

            return User(bot=self.bot, **rename_invalid_keys(row))
        elif insert_on_fail:
            await self.insert_user(insert_on_fail)
            return insert_on_fail
        else:
            return await self.insert_empty_user(user_id)

    async def fetch_cooldown(self, user_id: int) -> Cooldown:
        row = await self.conn.fetchrow(
            "SELECT * FROM cooldown WHERE user_id = $1",
            user_id,
        )

        from objects.user import Cooldown

        return Cooldown(bot=self.bot, **rename_invalid_keys(row)) if row else None

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
            _id=user_id, current_board=None, skip_confirm=False, cooldown_remind=False
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
        from objects.historyRecord import HistoryRecord

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

    async def add_cooldown(self, cooldown: Cooldown):
        await self.conn.execute(
            "INSERT INTO cooldown (user_id, cooldown_time) VALUES ($1, $2)",
            cooldown.user.id,
            cooldown.cooldown_time,
        )

    async def set_cooldown(self, cooldown: Cooldown):
        await self.conn.execute(
            "UPDATE cooldown SET cooldown_time = $1 WHERE user_id = $2",
            cooldown.cooldown_time,
            cooldown.user.id,
        )

    async def clear_cooldown(self, user_id: int):
        await self.conn.execute(
            "DELETE FROM cooldown WHERE user_id = $1",
            user_id,
        )

    async def add_blacklist(self, user_id: int):
        await self.conn.execute(
            "INSERT INTO blacklist (user_id, date_added) VALUES ($1, $2)",
            user_id,
            datetime.now(tz=timezone.utc),
        )

    async def remove_blacklist(self, user_id: int):
        await self.conn.execute(
            "DELETE FROM blacklist WHERE user_id = $1",
            user_id,
        )


def rename_invalid_keys(data: dict) -> dict:
    renames = {
        "id": "_id",
        "global": "_global",
    }
    return {renames.get(k, k) if k in renames else k: v for k, v in data.items()}
