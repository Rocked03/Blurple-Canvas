from config import *
import discord, datetime
from discord.ext import commands

description = "r/place for Discord" # fix
bot = commands.Bot(command_prefix=BOT_PREFIX, description=description)

bot.allowedusers = {204778476102877187, 226595531844091904}

bot.recentcog = None

bot.modroles = {
    "Admin":       443013283977494539,
    "Executive":   413213839866462220,
    "Moderator":   569015549225598976,
    "Helper":      442785212502507551,
}

def s(n : int): return 's' if n != 1 else ''
def areis(n : int): return 'are' if n != 1 else 'is'
def cint(codeinfo): return "{:,}".format(codeinfo)
def strfdelta(tdelta, fmt):
    d = {"days": tdelta.days}
    d["hours"], rem = divmod(tdelta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)

def dev():
    async def pred(ctx): return ctx.author.id in bot.allowedusers
    return commands.check(pred)

def mod():
    async def pred(ctx): return any(elem in [v for k, v in bot.modroles.items()] for elem in [i.id for i in ctx.author.roles])
    return commands.check(pred)



initial_extensions = [
    'cogs.canvas',
]

if __name__ == '__main__':
    for extension in initial_extensions:
        bot.load_extension(extension)




@bot.event
async def on_connect():
    print('Loaded Discord')
    activity = discord.Game(name="Starting up...")
    await bot.change_presence(status=discord.Status.idle, activity=activity)

@bot.event
async def on_ready():
    print('------')
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print(datetime.datetime.now().strftime("%d/%m/%Y %I:%M:%S%p UTC"))
    print('------')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name="pixels", type=discord.ActivityType.watching))
    bot.uptime = datetime.datetime.utcnow()


    bot.blurpleguild = bot.get_guild(412754940885467146)

    bot.appinfo = await self.bot.application_info()

@bot.check
async def globally_block_dms(ctx):
    return ctx.guild is not None

@bot.check
async def blacklist(ctx):
    return 573392328912404480 not in [r.id for r in bot.blurpleguild.get_member(ctx.author.id).roles]

@bot.check
def isnew(ctx):
    return ctx.author.created_at < datetime.datetime(2019, 5, 6, 12)

@bot.command(name='shutdown', aliases=["reboot"])
@dev()
async def shutdown(ctx):
    """Shuts down the bot"""
    try:
        embed = discord.Embed(timestamp=datetime.datetime.utcnow(), colour=0x7289da)
        embed.add_field(name="Shutting down<a:underscore:420740967939964928>", value="Blurplefied")
        await ctx.send(embed=embed)
        totaluptime = datetime.datetime.utcnow() - bot.uptime
        totaluptime = strfdelta(totaluptime, "{days} days, {hours} hours, {minutes} minutes, {seconds} seconds")
        print(f'Shutting down... Total uptime: {totaluptime}')
        await bot.logout()
    except Exception: 
        # await ctx.send('Something went wrong.')
        pass

@bot.command(hidden = True)
@dev()
async def fshutdown(ctx):
    await bot.logout()

@bot.command()
async def ping(ctx):
    """Checks the bot's latency"""
    latency=bot.latency*1000
    latency=round(latency,2)
    latency=str(latency)
    embed = discord.Embed(colour=0x7289da, timestamp=datetime.datetime.utcnow())
    embed.set_author(name="Ping!")
    embed.add_field(name='Bot latency', value=latency+"ms")
    await ctx.send(embed=embed)


@bot.group(name="cogs", aliases=["cog"])
@dev()
async def cogs(ctx):
    """Cog management"""
    return

@cogs.command(name = 'load')
@dev()
async def loadcog(ctx, *, cog: str):
    """Loads cog. Remember to use dot path. e.g: cogs.owner"""

    try: bot.load_extension(cog)
    except Exception as e: return await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
    else: await ctx.send(f'Successfully loaded `{cog}`.')
    print('---')
    print(f'{cog} was loaded.')
    print('---')

@cogs.command(name = 'unload')
@dev()
async def unloadcog(ctx, *, cog: str):
    """Unloads cog. Remember to use dot path. e.g: cogs.owner"""

    try: bot.unload_extension(cog)
    except Exception as e: return await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
    else: await ctx.send(f'Successfully unloaded `{cog}`.')
    print('---')
    print(f'{cog} was unloaded.')
    print('---')

@cogs.command(name = 'reload')
@dev()
async def reloadcog(ctx, *, cog: str):
    """Reloads cog. Remember to use dot path. e.g: cogs.owner"""

    try: bot.reload_extension(cog)
    except Exception as e: return await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
    else: await ctx.send(f'Successfully reloaded `{cog}`.')
    bot.recentcog = cog
    print('---')
    print(f'{cog} was reloaded.')
    print('---')

@bot.command(hidden = True, aliases = ['crr'])
@dev()
async def cogrecentreload(ctx):
    """Reloads most recent reloaded cog"""
    if not bot.recentcog: return await ctx.send("You haven't recently reloaded any cogs.")

    try: bot.reload_extension(bot.recentcog)
    except Exception as e: await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
    else: await ctx.send(f'Successfully reloaded `{bot.recentcog}`.')
    print('---')
    print(f'{bot.recentcog} was reloaded.')
    print('---')



try: bot.run(TOKEN)
except Exception: print("Whoops, bot failed to connect to Discord.")