from typing import Any, Generator

from asyncpg import Connection
from discord import Client

from objects.canvas import Canvas
from objects.color import Color
from objects.historyRecord import HistoryRecord
from objects.info import Info
from objects.participation import Participation


def rename_invalid_keys(data: dict) -> dict:
    renames = {
        "id": "_id",
        "global": "_global",
    }
    return {renames.get(k, k) if k in renames else k: v for k, v in data.items()}


class SQLManagement:
    def __init__(self, conn: Connection, bot: Client = None):
        self.conn = conn
        self.bot = bot

    async def fetch_canvas(self, canvas_id) -> Canvas:
        query = "SELECT * FROM canvas WHERE id = $1"
        row = await self.conn.fetchrow(query, canvas_id)
        return Canvas(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_all_colors(self) -> list[Color]:
        query = "SELECT * FROM color"
        rows = await self.conn.fetch(query)
        return [Color(bot=self.bot, **rename_invalid_keys(row)) for row in rows]

    async def fetch_history_records(
        self, canvas_id: int, user_id: int = None
    ) -> Generator[HistoryRecord, Any, None]:
        if user_id:
            query = "SELECT * FROM history WHERE canvas_id = $1 AND user_id = $2 ORDER BY timestamp"
            rows = await self.conn.fetch(query, canvas_id, user_id)
        else:
            query = "SELECT * FROM history WHERE canvas_id = $1 ORDER BY timestamp"
            rows = await self.conn.fetch(query, canvas_id)
        return (HistoryRecord(bot=self.bot, **rename_invalid_keys(row)) for row in rows)

    async def fetch_participation(self, guild_id: int, event_id: int) -> Participation:
        query = (
            "SELECT p.*, g.id, c.code, c.name, c.emoji_name, c.emoji_id "
            "FROM participation p "
            "left join guild g on p.guild_id = g.id "
            "left join public.color c on c.id = p.color_id "
            "WHERE guild_id = $1 AND event_id = $2"
        )
        row = await self.conn.fetchrow(query, guild_id, event_id)
        return Participation(bot=self.bot, **rename_invalid_keys(row))

    async def fetch_info(self) -> Info:
        query = "SELECT * FROM info"
        row = await self.conn.fetchrow(query)
        return Info(bot=self.bot, **rename_invalid_keys(row))

    async def insert_color(self, color: Color):
        query = (
            "INSERT INTO color (id, code, emoji_name, emoji_id, global, name, rgba) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7)"
        )
        await self.conn.execute(
            query,
            color.code,
            color.emoji_name,
            color.emoji_id,
            color.is_global,
            color.name,
            color.rgba,
        )  # TODO: color ID auto increment?

    async def insert_participation(self, participation: Participation):
        query = (
            "INSERT INTO participation (guild_id, event_id, custom_color, color_id) "
            "VALUES ($1, $2, $3, $4)"
        )
        await self.conn.execute(
            query,
            participation.guild_id,
            participation.event_id,
            participation.custom_color,
            participation.color_id,
        )

    async def insert_history_record(self, history_record: HistoryRecord):
        query = (
            "INSERT INTO history (canvas_id, user_id, x, y, color_id, timestamp) "
            "VALUES ($1, $2, $3, $4, $5, $6)"
        )
        await self.conn.execute(
            query,
            history_record.pixel.canvas_id,
            history_record.user_id,
            history_record.pixel.x,
            history_record.pixel.y,
            history_record.pixel.color_id,
            history_record.timestamp,
        )
