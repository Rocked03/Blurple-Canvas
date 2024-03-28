import traceback
from datetime import datetime, timezone
from typing import Literal, Optional

from discord import (
    HTTPException,
    Object,
    ActivityType,
    Activity,
    Status,
    Game,
    MemberCacheFlags,
    Intents,
    User,
)
from discord.ext import commands
from discord.ext.commands import Bot

from config import BOT_PREFIX, OWNER_IDS, TOKEN
from objects.cache import Cache


class CanvasBot(Bot):
    async def is_owner(self, user: User):
        if user.id in OWNER_IDS:  # Implement your own conditions here
            return True

        # Else fall back to the original
        return await super().is_owner(user)

    async def setup_hook(self):
        initial_extensions = ["cogs.canvas"]

        for extension in initial_extensions:
            await bot.load_extension(extension)


intents = Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True

description = "Blurple Canvas for Project Blurple"


bot = CanvasBot(
    command_prefix=lambda _bot, _message: BOT_PREFIX,
    description=description,
    intents=intents,
    chunk_guilds_at_startup=False,
    member_cache_flags=MemberCacheFlags.all(),
)

bot.recent_cog = None
bot.help = bot.description
bot.cache: dict[int, Cache] = {}

bot.remove_command("help")


@bot.event
async def on_connect():
    print("Loaded Discord")
    await bot.change_presence(status=Status.idle, activity=Game(name="Starting up..."))


@bot.event
async def on_ready():
    print(
        "------\n"
        "Logged in as\n"
        f"{bot.user.name} ({bot.user.id})\n"
        f"{datetime.now(timezone.utc).strftime('%d/%m/%Y %I:%M:%S%p UTC')}\n"
        f"------"
    )
    await bot.change_presence(
        status=Status.online,
        activity=Activity(name="pixels", type=ActivityType.watching),
    )
    bot.uptime = datetime.now(timezone.utc)

    bot.appinfo = await bot.application_info()


@bot.check
async def globally_block_dms(ctx):
    return ctx.guild is not None


@bot.group(name="cogs", aliases=["cog"])
@commands.is_owner()
async def cogs(ctx):
    """Cog management"""
    return


@cogs.command(name="load")
@commands.is_owner()
async def load_cog(ctx, *, cog: str):
    """Loads cog. Remember to use dot path. e.g: cogs.owner"""
    try:
        await bot.load_extension(cog)
    except Exception:
        traceback.print_exc()
    else:
        await ctx.send(f"Successfully loaded `{cog}`.")
        print(f"---\n{cog} was loaded.\n---")


@cogs.command(name="unload")
@commands.is_owner()
async def unload_cog(ctx, *, cog: str):
    """Unloads cog. Remember to use dot path. e.g: cogs.owner"""
    try:
        await bot.unload_extension(cog)
    except Exception:
        traceback.print_exc()
    else:
        await ctx.send(f"Successfully unloaded `{cog}`.")
        print(f"---\n{cog} was unloaded.\n---")


@cogs.command(name="reload")
@commands.is_owner()
async def reload_cog(ctx, *, cog: str):
    """Reloads cog. Remember to use dot path. e.g: cogs.owner"""
    bot.recent_cog = cog
    try:
        await bot.reload_extension(cog)
    except Exception:
        traceback.print_exc()
    else:
        await ctx.send(f"Successfully reloaded `{cog}`.")
        print(f"---\n{cog} was reloaded.\n---")


@bot.command(hidden=True, aliases=["crr"])
@commands.is_owner()
async def cog_recent_reload(ctx):
    """Reloads most recent reloaded cog"""
    if not bot.recent_cog:
        return await ctx.send("You haven't recently reloaded any cogs.")

    try:
        await bot.reload_extension(bot.recent_cog)
    except Exception as e:
        await ctx.send(f"**ERROR:** {type(e).__name__} - {e}")
    else:
        await ctx.send(f"Successfully reloaded `{bot.recent_cog}`.")
        print(f"---\n{bot.recent_cog} was reloaded.\n---")


@bot.command()
@commands.is_owner()
async def servers(ctx):
    await ctx.send("\n".join(f"{i.name} ({i.id})" for i in bot.guilds))


@bot.command()
@commands.is_owner()
async def sync(
    ctx,
    guilds: commands.Greedy[Object],
    spec: Optional[Literal["~"]] = None,
) -> None:
    if not guilds:
        if spec == "~":
            fmt = await bot.tree.sync(guild=ctx.guild)
        else:
            fmt = await bot.tree.sync()

        await ctx.send(
            f"Synced {len(fmt)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    assert guilds is not None
    fmt = 0
    for guild in guilds:
        try:
            await bot.tree.sync(guild=guild)
        except HTTPException:
            pass
        else:
            fmt += 1

    await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")


try:
    bot.run(TOKEN)
except Exception as e:
    print("Whoops, bot failed to connect to Discord.")
    print(e)
