import asyncio
import asyncpg
import os
from config import POSTGRES_CREDENTIALS

OUTPUT_DIR = "generated"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "participants.txt")
CANVAS_ID = 2025


async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)  # Create folder if missing

    conn = await asyncpg.connect(**POSTGRES_CREDENTIALS)

    query = """
    SELECT DISTINCT h.user_id
    FROM history h
    LEFT JOIN blacklist b ON h.user_id = b.user_id
    WHERE h.canvas_id = $1 AND b.user_id IS NULL
    ORDER BY h.user_id::bigint ASC;
    """

    rows = await conn.fetch(query, CANVAS_ID)
    await conn.close()

    user_ids = [str(row["user_id"]) for row in rows]

    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(user_ids))

    print(f"Saved {len(user_ids)} user IDs to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
