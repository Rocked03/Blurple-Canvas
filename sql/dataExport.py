import asyncio
import json
from os import mkdir, path
from typing import Optional, Any, Generator

import asyncpg
from asyncpg import Connection

from config import POSTGRES_CREDENTIALS
from objects.canvas import Canvas
from objects.color import Palette, Color
from objects.frame import Frame
from objects.historyRecord import HistoryRecord
from objects.pixel import Pixel
from objects.stats import Leaderboard, Ranking, GuildStats
from objects.timer import Timer
from sql.sqlManager import SQLManager


class Config:
    event_id: int = 2024
    canvas_ids: list[int] = [2024]
    data_folder: str = "generated"


CONFIG = Config()


class DTO:
    def to_json(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class ColorJsonDTO(DTO):
    def __init__(self, color: Color):
        self.id: int = color.id
        self.code: str = color.code
        self.name: str = color.name
        self.rgba: tuple[int, int, int, int] = color.rgba
        self.guild: Optional[str] = str(color.guild.id) if color.guild else None
        self.is_global: bool = color.is_global


class HistoryJsonDTO(DTO):
    def __init__(self, record: HistoryRecord):
        self.id: int = record.id
        self.x: int = record.pixel.x
        self.y: int = record.pixel.y
        self.color: int = record.pixel.color.id
        self.time: str = record.timestamp.isoformat()
        self.user: Optional[str] = str(record.user.id) if record.user else None


class CanvasDTO(DTO):
    def __init__(self, canvas: Canvas, frame: Frame):
        self.id: int = canvas.id
        self.name: str = canvas.name
        self.width: int = canvas.width
        self.height: int = canvas.height
        self.cooldown_length: int = canvas.cooldown_length
        self.start_coordinates: tuple[int, int] = canvas.start_coordinates.to_tuple()
        self.pixels: list[list[int]] = pixels_to_list(
            frame.pixels, canvas.width, canvas.height
        )


class RankingDTO(DTO):
    def __init__(self, ranking: Ranking):
        self.user_id: str = str(ranking.user_id)
        self.ranking: int = ranking.ranking
        self.total_pixels: int = ranking.total_pixels


class GuildStatsDTO(DTO):
    def __init__(self, stats: GuildStats):
        self.total_pixels: int = stats.total_pixels
        self.place_frequency: Optional[str] = (
            stats.place_frequency.total_seconds() if stats.place_frequency else None
        )
        self.most_recent_timestamp: Optional[str] = (
            stats.most_recent_timestamp.isoformat()
            if stats.most_recent_timestamp
            else None
        )
        self.leaderboard: Optional[Leaderboard] = stats.leaderboard


async def connect(credentials) -> Connection:
    return await asyncpg.connect(**credentials)


def json_from_palette(palette: Palette) -> list[ColorJsonDTO.__dict__]:
    return [ColorJsonDTO(color).to_json() for color in palette]


def json_from_history(
    history: Generator[HistoryRecord, Any, None]
) -> list[HistoryJsonDTO.__dict__]:
    return [HistoryJsonDTO(record).to_json() for record in history]


def json_from_leaderboard(
    leaderboard: list[Ranking],
) -> int | list[RankingDTO.__dict__]:
    leaderboard.sort(key=lambda r: r.ranking)
    return [RankingDTO(ranking).to_json() for ranking in leaderboard]


def pixels_to_list(pixels: list[Pixel], width: int, height: int) -> list[list[int]]:
    result = [[0 for _ in range(width)] for _ in range(height)]
    for pixel in pixels:
        result[pixel.y][pixel.x] = pixel.color.id
    return result


def json_from_canvas(canvas: Canvas, frame: Frame) -> CanvasDTO.__dict__:
    return CanvasDTO(canvas, frame).to_json()


def json_from_guild_stats(stats: Optional[GuildStats]) -> GuildStatsDTO.__dict__:
    return GuildStatsDTO(stats).to_json() if stats else {}


def save_to_json(data: dict | list, file_name: str):
    if not path.exists(CONFIG.data_folder):
        mkdir(CONFIG.data_folder)
    if not path.exists(f"{CONFIG.data_folder}/stats"):
        mkdir(f"{CONFIG.data_folder}/stats")

    with open(f"{CONFIG.data_folder}/{file_name}.json", "w") as f:
        json.dump(data, f, indent=2)


async def fetch_colors(sql: SQLManager) -> Palette:
    return await sql.fetch_colors_by_participation(CONFIG.event_id)


async def fetch_history(
    sql: SQLManager,
) -> dict[int, Generator[HistoryRecord, Any, None]]:
    return {
        canvas_id: await sql.fetch_history_records(canvas_id)
        for canvas_id in CONFIG.canvas_ids
    }


async def fetch_canvas(sql: SQLManager) -> dict[int, (Canvas, Frame)]:
    canvases: dict[int, (Canvas, Frame)] = {}

    for canvas_id in CONFIG.canvas_ids:
        canvas = await sql.fetch_canvas_by_id(canvas_id)
        full_frame = await canvas.get_frame_full(sql)
        await full_frame.load_pixels(sql)

        canvases[canvas_id] = (canvas, full_frame)

    return canvases


async def fetch_leaderboard(sql: SQLManager) -> dict[int, list[Ranking]]:
    leaderboards = {}
    for canvas_id in CONFIG.canvas_ids:
        leaderboard = await sql.fetch_leaderboard(
            canvas_id, limit=1000000000, max_rank=1000000000
        )
        leaderboards[canvas_id] = leaderboard
    return leaderboards


async def fetch_leaderboard_guild(
    sql: SQLManager, canvas_id: int, guild_id: int
) -> list[Ranking]:
    return await sql.fetch_leaderboard_guild(
        canvas_id, guild_id, limit=1000000000, max_rank=1000000000
    )


async def fetch_participation_ids(sql: SQLManager) -> list[int]:
    participations = await sql.fetch_participation_by_event(CONFIG.event_id)
    return [participation.guild_id for participation in participations]


async def fetch_leaderboard_guilds(
    sql: SQLManager,
    guild_id: int,
) -> dict[int, list[Ranking]]:
    return {
        canvas_id: await fetch_leaderboard_guild(sql, canvas_id, guild_id)
        for canvas_id in CONFIG.canvas_ids
    }


async def fetch_guild_stats(sql: SQLManager, guild_id: int) -> dict[int, GuildStats]:
    return {
        canvas_id: await sql.fetch_guild_stats(guild_id, canvas_id)
        for canvas_id in CONFIG.canvas_ids
    }


async def colors_to_json(sql: SQLManager):
    palette = await fetch_colors(sql)
    colors = json_from_palette(palette)
    save_to_json(colors, "colors")


async def history_to_json(sql: SQLManager):
    history = await fetch_history(sql)
    for canvas_id, records in history.items():
        records = json_from_history(records)
        save_to_json(records, f"history_{canvas_id}")


async def canvas_to_json(sql: SQLManager):
    canvas_data = await fetch_canvas(sql)
    for canvas_id, (canvas, frame) in canvas_data.items():
        data = json_from_canvas(canvas, frame)
        save_to_json(data, f"canvas_{canvas_id}")


async def stats_to_json(sql: SQLManager):
    timer = Timer()

    leaderboards = await fetch_leaderboard(sql)
    data = [
        {"canvas_id": canvas_id, "leaderboard": json_from_leaderboard(leaderboard)}
        for canvas_id, leaderboard in leaderboards.items()
    ]
    save_to_json(data, f"stats/leaderboard_global")

    timer.mark("Global leaderboard")

    participation_ids = await fetch_participation_ids(sql)
    timer.mark("Fetched participation IDs")

    for participation_id in participation_ids:
        leaderboards = await fetch_leaderboard_guilds(sql, participation_id)
        guild_stats = await fetch_guild_stats(sql, participation_id)
        data = [
            {
                "canvas_id": canvas_id,
                "leaderboard": json_from_leaderboard(
                    leaderboards[canvas_id] if canvas_id in leaderboards else []
                ),
                "stats": json_from_guild_stats(
                    guild_stats[canvas_id] if canvas_id in guild_stats else None
                ),
            }
            for canvas_id in CONFIG.canvas_ids
        ]
        save_to_json(data, f"stats/stats_{participation_id}")

        timer.mark(f"Guild leaderboard {participation_id}")


async def main():
    credentials = POSTGRES_CREDENTIALS

    timer = Timer()
    conn = await connect(credentials)
    sql = SQLManager(conn)
    timer.mark("Connected")

    await stats_to_json(sql)

    timer.mark("Done")


if __name__ == "__main__":
    asyncio.run(main())
