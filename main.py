import asyncio
import datetime
import re
import typing

import discord
from discord.ext import commands

from config import *
from objects.cache import Cache


# logging.basicConfig(level=logging.INFO)


class CanvasBot(commands.Bot):
    async def is_owner(self, user: discord.User):
        if user.id in self.allowed_users:  # Implement your own conditions here
            return True

        # Else fall back to the original
        return await super().is_owner(user)

    async def setup_hook(self):
        initial_extensions = ["cogs.canvas"]

        for extension in initial_extensions:
            await bot.load_extension(extension)


intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True

description = "Blurple Canvas for Project Blurple"  # fix


async def get_pre(bot, message):
    return BOT_PREFIX


bot = CanvasBot(
    command_prefix=get_pre,
    description=description,
    intents=intents,
    chunk_guilds_at_startup=False,
)

bot.allowed_users = {204778476102877187, 226595531844091904, 248245568004947969}

bot.recentcog = None

bot.modroles = {
    "Admin": 443013283977494539,
    "Executive": 413213839866462220,
    "Exec Assist": 470272155876065280,
    "Moderator": 569015549225598976,
    "Helper": 442785212502507551,
}

bot.help = bot.description

bot.cache: dict[int, Cache] = {}


def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def dev():
    async def pred(ctx):
        return ctx.author.id in bot.allowed_users

    return commands.check(pred)


def mod():
    async def pred(ctx):
        return any(
            elem in [v for k, v in bot.modroles.items()]
            for elem in [i.id for i in ctx.author.roles]
        )

    return commands.check(pred)


@bot.event
async def on_connect():
    print("Loaded Discord")
    activity = discord.Game(name="Starting up...")
    await bot.change_presence(status=discord.Status.idle, activity=activity)


@bot.event
async def on_ready():
    print("------")
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    print(datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S%p UTC"))
    print("------")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(name="pixels", type=discord.ActivityType.watching),
    )
    bot.uptime = datetime.datetime.utcnow()

    while True:
        await asyncio.sleep(1)
        try:
            bot.blurple_guild = bot.get_guild(412754940885467146)
            if bot.blurple_guild:
                break
        except AttributeError:
            pass

    await bot.blurple_guild.chunk()

    bot.appinfo = await bot.application_info()


@bot.check
async def globally_block_dms(ctx):
    return ctx.guild is not None


@bot.check
async def blacklist(ctx):
    try:
        return 573392328912404480 not in [
            r.id for r in (await bot.blurple_guild.fetch_member(ctx.author.id)).roles
        ]
    except Exception:
        return False


# @bot.check
# async def server(ctx):
#     return ctx.guild.id in list(bot.partners.keys()).append(412754940885467146)


@bot.check
def isnew(ctx):
    return True
    # return ctx.author.created_at < datetime.datetime(2019, 5, 6, 12)


@bot.command(name="shutdown", aliases=["reboot"])
@dev()
async def shutdown(ctx):
    """Shuts down the bot"""
    try:
        embed = discord.Embed(timestamp=datetime.datetime.utcnow(), colour=0x7289DA)
        embed.add_field(
            name="Shutting down<a:underscore:420740967939964928>", value="Blurplefied"
        )
        await ctx.send(embed=embed)
        total_uptime = datetime.datetime.utcnow() - bot.uptime
        total_uptime = strfdelta(
            total_uptime,
            "{days} days, {hours} hours, {minutes} minutes, {seconds} seconds",
        )
        print(f"Shutting down... Total uptime: {total_uptime}")
        await bot.close()
    except Exception:
        # await ctx.send('Something went wrong.')
        pass


@bot.command(hidden=True)
@dev()
async def fshutdown(ctx):
    await bot.logout()


@bot.command()
async def ping(ctx):
    """Checks the bot's latency"""
    latency = bot.latency * 1000
    latency = round(latency, 2)
    latency = str(latency)
    embed = discord.Embed(colour=0x7289DA, timestamp=datetime.datetime.utcnow())
    embed.set_author(name="Ping!")
    embed.add_field(name="Bot latency", value=latency + "ms")
    embed.set_footer(
        text=f"{str(ctx.author)} | {bot.user.name} | {ctx.prefix}{ctx.command.name}",
        icon_url=bot.user.avatar,
    )
    await ctx.send(embed=embed)


_mentions_transforms = {"@everyone": "@\u200beveryone", "@here": "@\u200bhere"}

_mention_pattern = re.compile("|".join(_mentions_transforms.keys()))

bot.remove_command("help")


@bot.group(name="cogs", aliases=["cog"])
@dev()
async def cogs(ctx):
    """Cog management"""
    return


@cogs.command(name="load")
@dev()
async def load_cog(ctx, *, cog: str):
    """Loads cog. Remember to use dot path. e.g: cogs.owner"""

    try:
        await bot.load_extension(cog)
    except Exception as e:
        return await ctx.send(f"**ERROR:** {type(e).__name__} - {e}")
    else:
        await ctx.send(f"Successfully loaded `{cog}`.")
    print("---")
    print(f"{cog} was loaded.")
    print("---")


@cogs.command(name="unload")
@dev()
async def unload_cog(ctx, *, cog: str):
    """Unloads cog. Remember to use dot path. e.g: cogs.owner"""

    try:
        await bot.unload_extension(cog)
    except Exception as e:
        return await ctx.send(f"**ERROR:** {type(e).__name__} - {e}")
    else:
        await ctx.send(f"Successfully unloaded `{cog}`.")
    print("---")
    print(f"{cog} was unloaded.")
    print("---")


@cogs.command(name="reload")
@dev()
async def reload_cog(ctx, *, cog: str):
    """Reloads cog. Remember to use dot path. e.g: cogs.owner"""

    try:
        await bot.reload_extension(cog)
    except Exception as e:
        return await ctx.send(f"**ERROR:** {type(e).__name__} - {e}")
    else:
        await ctx.send(f"Successfully reloaded `{cog}`.")
    bot.recentcog = cog
    print("---")
    print(f"{cog} was reloaded.")
    print("---")


@bot.command(hidden=True, aliases=["crr"])
@dev()
async def cog_recent_reload(ctx):
    """Reloads most recent reloaded cog"""
    if not bot.recentcog:
        return await ctx.send("You haven't recently reloaded any cogs.")

    try:
        await bot.reload_extension(bot.recentcog)
    except Exception as e:
        await ctx.send(f"**ERROR:** {type(e).__name__} - {e}")
    else:
        await ctx.send(f"Successfully reloaded `{bot.recentcog}`.")
    print("---")
    print(f"{bot.recentcog} was reloaded.")
    print("---")


@bot.command()
@commands.is_owner()
async def servers(ctx):
    await ctx.send("\n".join([i.name for i in bot.guilds]))


@bot.command()
@commands.is_owner()
async def sync(
    ctx,
    guilds: commands.Greedy[discord.Object],
    spec: typing.Optional[typing.Literal["~"]] = None,
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
        except discord.HTTPException:
            pass
        else:
            fmt += 1

    await ctx.send(f"Synced the tree to {fmt}/{len(guilds)} guilds.")


try:
    bot.run(TOKEN)
except Exception as e:
    print("Whoops, bot failed to connect to Discord.")
    print(e)
