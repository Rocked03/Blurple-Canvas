import asyncio
import asyncpg
import json
import os
from asyncpg import Connection
from config import POSTGRES_CREDENTIALS
from objects.timer import Timer

TIMER = Timer()


class Config:
    canvas_id: int = 2025
    event_id: int = 2025
    output_dir: str = "generated"


async def connect(credentials) -> Connection:
    return await asyncpg.connect(**credentials)


async def get_canvas_metadata(conn: Connection, canvas_id: int) -> dict:
    query = """
    SELECT id, name, width, height, cooldown_length, start_coordinates
    FROM canvas
    WHERE id = $1;
    """
    return await conn.fetchrow(query, canvas_id)


async def get_canvas_pixels(
    conn: Connection, canvas_id: int, width: int, height: int
) -> list:
    query = """
    SELECT x, y, color_id
    FROM pixel
    WHERE canvas_id = $1;
    """
    rows = await conn.fetch(query, canvas_id)

    # Initialize empty grid
    pixel_grid = [[0 for _ in range(width)] for _ in range(height)]

    for row in rows:
        x, y, color_id = row["x"], row["y"], row["color_id"]
        pixel_grid[y][x] = color_id

    return pixel_grid


async def get_colors(conn: Connection, event_id: int) -> list:
    query = """
    SELECT 
        c.id, c.code, c.name, c.rgba, 
        p.guild_id, c.global
    FROM color c
    LEFT JOIN participation p ON c.id = p.color_id AND p.event_id = $1
    WHERE c.global = TRUE OR p.event_id = $1;
    """
    rows = await conn.fetch(query, event_id)

    colors = []
    for row in rows:
        color = {
            "id": row["id"],
            "code": row["code"],
            "name": row["name"],
            "rgba": row["rgba"],
            "is_global": row["global"],
        }
        if not row["global"]:
            color["guild"] = str(row["guild_id"])  # Convert bigint to string for JSON
        colors.append(color)

    return colors


async def get_history(conn: Connection, canvas_id: int) -> list:
    query = """
    SELECT id, x, y, color_id, timestamp, user_id
    FROM history
    WHERE canvas_id = $1
    ORDER BY timestamp ASC;
    """
    rows = await conn.fetch(query, canvas_id)

    history = []
    for row in rows:
        history.append(
            {
                "id": row["id"],
                "x": row["x"],
                "y": row["y"],
                "color": row["color_id"],
                "time": row["timestamp"].isoformat(),
                "user": str(row["user_id"]),
            }
        )

    return history


async def export_guild_stats(conn: Connection, canvas_id: int, output_dir: str):
    stats_dir = os.path.join(output_dir, "stats")
    os.makedirs(stats_dir, exist_ok=True)

    # Get all stats for the specified canvas
    stats_query = """
    SELECT * FROM guild_stats
    WHERE canvas_id = $1;
    """
    stats_rows = await conn.fetch(stats_query, canvas_id)

    # Organize stats by guild_id
    stats_by_guild = {}
    for row in stats_rows:
        guild_id = str(row["guild_id"])
        stats_by_guild[guild_id] = {
            "canvas_id": row["canvas_id"],
            "stats": {
                "total_pixels": row["total_pixels"],
                "place_frequency": (
                    row["place_frequency"].total_seconds()
                    if row["place_frequency"] is not None
                    else 0
                ),
                "most_recent_timestamp": row["most_recent_timestamp"].isoformat(),
            },
            "leaderboard": [],
        }

    # Get leaderboard for those guilds and canvas
    leaderboard_query = """
    SELECT * FROM leaderboard_guild
    WHERE canvas_id = $1
    ORDER BY rank ASC;
    """
    leaderboard_rows = await conn.fetch(leaderboard_query, canvas_id)

    for row in leaderboard_rows:
        guild_id = str(row["guild_id"])
        if guild_id in stats_by_guild:
            stats_by_guild[guild_id]["leaderboard"].append(
                {
                    "user_id": str(row["user_id"]),
                    "ranking": row["rank"],
                    "total_pixels": row["total_pixels"],
                }
            )

    # Write individual JSON files
    for guild_id, data in stats_by_guild.items():
        with open(os.path.join(stats_dir, f"stats_{guild_id}.json"), "w") as f:
            json.dump([data], f, indent=2)


async def export_global_leaderboard(conn: Connection, canvas_id: int, output_dir: str):
    stats_dir = os.path.join(output_dir, "stats")
    os.makedirs(stats_dir, exist_ok=True)

    query = """
    SELECT user_id, rank, total_pixels
    FROM leaderboard
    WHERE canvas_id = $1
    ORDER BY rank ASC;
    """
    rows = await conn.fetch(query, canvas_id)

    leaderboard = [
        {
            "user_id": str(row["user_id"]),
            "ranking": row["rank"],
            "total_pixels": row["total_pixels"],
        }
        for row in rows
    ]

    output = {"canvas_id": canvas_id, "leaderboard": leaderboard}

    with open(os.path.join(stats_dir, "leaderboard_global.json"), "w") as f:
        json.dump(output, f, indent=2)


async def main():
    os.makedirs(Config.output_dir, exist_ok=True)
    conn = await connect(POSTGRES_CREDENTIALS)
    TIMER.mark("Connected to SQL")

    canvas = await get_canvas_metadata(conn, Config.canvas_id)
    TIMER.mark("Fetched canvas metadata")

    pixel_grid = await get_canvas_pixels(
        conn, Config.canvas_id, canvas["width"], canvas["height"]
    )
    TIMER.mark("Fetched and built pixel grid")

    output = {
        "id": canvas["id"],
        "name": canvas["name"],
        "width": canvas["width"],
        "height": canvas["height"],
        "cooldown_length": canvas["cooldown_length"],
        "start_coordinates": canvas["start_coordinates"],
        "pixels": pixel_grid,
    }

    canvas_path = os.path.join(Config.output_dir, f"canvas_{Config.canvas_id}.json")
    with open(canvas_path, "w") as f:
        json.dump(output, f, indent=2)

    TIMER.mark(f"Saved canvas_{Config.canvas_id}.json")

    colors = await get_colors(conn, Config.event_id)
    TIMER.mark("Fetched colors")

    colors_path = os.path.join(Config.output_dir, f"color_{Config.canvas_id}.json")
    with open(colors_path, "w") as f:
        json.dump(colors, f, indent=2)

    TIMER.mark(f"Saved color_{Config.canvas_id}.json")

    history = await get_history(conn, Config.canvas_id)
    TIMER.mark("Fetched history")

    history_path = os.path.join(Config.output_dir, f"history_{Config.canvas_id}.json")
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)

    TIMER.mark(f"Saved history_{Config.canvas_id}.json")

    # await export_guild_stats(conn, Config.canvas_id, Config.output_dir)
    # TIMER.mark("Exported stats for all guilds on this canvas")

    await export_global_leaderboard(conn, Config.canvas_id, Config.output_dir)
    TIMER.mark("Exported global leaderboard")


if __name__ == "__main__":
    asyncio.run(main())
