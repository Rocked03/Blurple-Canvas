import asyncio
from datetime import datetime, timezone

from asyncpg import create_pool
from discord import Intents
from discord.ext.commands import Bot

from config import TOKEN, POSTGRES_CREDENTIALS
from objects.imager import Imager
from sql.sqlManager import SQLManager


class CanvasBannerBot(Bot):
    pass


bot = CanvasBannerBot(command_prefix=None, intents=Intents.none())


@bot.event
async def on_ready():
    print(
        f"------\n"
        f"Logged in as\n"
        f"{bot.user.name}\n"
        f"{bot.user.id}\n"
        f"{datetime.now(timezone.utc).strftime('%d/%m/%Y %I:%M:%S%p UTC')}\n"
        f"------"
    )

    bot.pool = await create_pool(**POSTGRES_CREDENTIALS)

    bot.loop.create_task(update_banner_loop())


async def update_banner_loop():
    while True:
        # Calculate the time to the next 6th hour
        interval = 6  # 1, 2, 3, 4, 6, 8, 12, 24
        now = datetime.now(timezone.utc)
        next_hour = ((now.hour // interval + 1) * interval) % 24
        next_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
        if next_time < now:
            next_time = next_time.replace(day=now.day + 1)

        # Sleep until the next 6th hour
        print(f"Sleeping until {next_time}")
        await asyncio.sleep((next_time - now).total_seconds())

        await update_banner()
        print(
            f"Banner updated {(datetime.now(timezone.utc) - next_time).total_seconds():.0f}s - {datetime.now(timezone.utc).strftime('%d/%m/%Y %I:%M:%S%p UTC')}"
        )


async def update_banner():
    conn = await bot.pool.acquire()
    sql = SQLManager(conn)

    info = await sql.fetch_info()
    if info is not None and info.default_canvas_id:
        canvas = await sql.fetch_canvas_by_id(info.default_canvas_id)
        frame = await canvas.get_frame_full(sql)
        image = frame.generate_image(zoom=2)

        gif_bytes, gif_size = Imager.create_scrolling_gif_banner(image)

        # if gif_size (in bytes) is less than 1024KB
        if gif_size < 1024 * 1024:
            await bot.user.edit(banner=gif_bytes.read())

    await sql.close()


try:
    bot.run(TOKEN)
except Exception as e:
    print("Whoops, bot failed to connect to Discord.")
    print(e)
