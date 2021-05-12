from config import *
import discord, datetime, re, asyncio
from discord.ext import commands
import logging

# logging.basicConfig(level=logging.INFO)

class CanvasBot(commands.Bot):
    async def is_owner(self, user: discord.User):
        if user.id in self.allowedusers:  # Implement your own conditions here
            return True

        # Else fall back to the original
        return await super().is_owner(user)

intents = discord.Intents.default()
intents.members = True

description = "Blurple Canvas for Project Blurple" # fix
async def get_pre(bot, message): return BOT_PREFIX
bot = CanvasBot(command_prefix=get_pre, description=description, intents=intents, chunk_guilds_at_startup=False)

bot.allowedusers = {204778476102877187, 226595531844091904, 248245568004947969}

bot.recentcog = None

bot.modroles = {
    "Admin":       443013283977494539,
    "Executive":   413213839866462220,
    "Exec Assist": 470272155876065280,
    "Moderator":   569015549225598976,
    "Helper":      442785212502507551,
}

bot.help = bot.description

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
    'cogs.colours',
    'jishaku'
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


    while True:
        await asyncio.sleep(1)
        try:
            bot.blurpleguild = bot.get_guild(412754940885467146)
            if bot.blurpleguild: break
        except AttributeError:
            pass

    await bot.blurpleguild.chunk()

    bot.appinfo = await bot.application_info()

@bot.check
async def globally_block_dms(ctx):
    return ctx.guild is not None

@bot.check
async def blacklist(ctx):
    try: return 573392328912404480 not in [r.id for r in (await bot.blurpleguild.fetch_member(ctx.author.id)).roles]
    except Exception: return False

# @bot.check
# async def server(ctx):
#     return ctx.guild.id in list(bot.partners.keys()).append(412754940885467146)

@bot.check
def isnew(ctx):
    return True
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
    embed.set_footer(
                    text=f"{str(ctx.author)} | {bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=bot.user.avatar_url)
    await ctx.send(embed=embed)



_mentions_transforms = {
    '@everyone': '@\u200beveryone',
    '@here': '@\u200bhere'
}

_mention_pattern = re.compile('|'.join(_mentions_transforms.keys()))

bot.remove_command('help')

@bot.command(name="help", aliases=['commands'])
async def help(ctx, *commands : str):
    """Displays this message."""
    try:
        def repl(obj):
            return _mentions_transforms.get(obj.group(0), '')

        if len(commands) == 0:
            embed = await helpformatter(ctx, bot)
        else:
            name = _mention_pattern.sub(repl, commands[0])
            command = bot.all_commands.get(name)
            if command is None:
                await ctx.send(bot.command_not_found.format(name))
                return

            for key in commands[1:]:
                try:
                    key = _mention_pattern.sub(repl, key)
                    command = command.all_commands.get(key)
                    if command is None:
                        await ctx.send(bot.command_not_found.format(key))
                        return
                except AttributeError:
                    await ctx.send(bot.command_has_no_subcommands.format(command, key))
                    return

            embed = await helpformatter(ctx, command)

        await ctx.author.send(embed=embed)
        await ctx.send(f"{ctx.author.mention}, sent to your DMs!")
    except Exception as e:
        print(e)

async def helpformatter(ctx, command):
    def spacestrip(x):
        if x == '': return ''
        else: return ' '

    embed = discord.Embed(colour=discord.Colour.blurple(), description=command.help)
    embed.set_footer(icon_url=bot.user.avatar_url)
    try: 
        embed.set_author(name=f'Bot command - {command.qualified_name}')
        try:
            command.commands
            embed.set_footer(text=f'{str(ctx.author)} | {bot.user.name} | Showing commands for \'{command.qualified_name}\' | To see more info on a command, type {ctx.prefix}help {command.qualified_name} <command>')
        except Exception:  embed.set_footer(text=f'Showing commands for \'{command.qualified_name}\'')
    except AttributeError: 
        embed.set_author(name=f'Bot commands')
        embed.set_footer(text=f'{str(ctx.author)} | {bot.user.name} | To see more info on a command, type {ctx.prefix}help <command>')
    try:
        params = []
        for param, specs in dict(command.clean_params).items():
            spec = specs.replace(annotation=specs.empty)
            if spec.default == None: spec = spec.replace(default=specs.empty)
            params.append(f"<{spec}>")
        paramsstr = " ".join(params)
        commandname = command.name
        if len(command.aliases) != 0: commandname = f'[{command.name}|{"|".join(command.aliases)}]'
        embed.add_field(name="Usage", value=f"`{ctx.prefix}{command.full_parent_name.strip()}{spacestrip(command.full_parent_name)}{commandname.strip()} {paramsstr}`", inline=False)
    except Exception:
        pass

    try:
        for subcommand in sorted(command.commands, key=lambda item: item.name):
            if subcommand.hidden: continue
            try: 
                if not(await subcommand.can_run(ctx)): continue
            except Exception: continue

            if subcommand.help == None: desc = ''
            else: desc = subcommand.help
            params = []
            for param, specs in dict(subcommand.clean_params).items():
                spec = specs.replace(annotation=specs.empty)
                if spec.default == None: spec = spec.replace(default=specs.empty)
                params.append(f"<{spec}>")
            paramsstr = " ".join(params)
            paramsstr = f"{ctx.prefix}{subcommand.full_parent_name.strip()}{spacestrip(subcommand.full_parent_name)}{subcommand.name.strip()} {paramsstr}"
            try: 
                subsubcommands = []
                for c in sorted(subcommand.commands, key=lambda item: item.name):
                    if (not(c.hidden) and await c.can_run(ctx)): subsubcommands.append(c.name)
            except Exception: subsubcommands = None
            if subsubcommands != None and len(subsubcommands) != 0: 
                subsubcommandtxt = "`" + "` `".join(subsubcommands) + "`"
                subsubcommandtxt = f"| {subsubcommandtxt}"
            else: subsubcommandtxt = ''
            embed.add_field(name=subcommand.name, value=f'{desc} \n`{paramsstr}` {subsubcommandtxt}', inline=False)
    except Exception as e:
        print(e)

    return embed


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


@bot.command()
@commands.is_owner()
async def servers(ctx):
    await ctx.send('\n'.join([i.name for i in bot.guilds]))




try: bot.run(TOKEN)
except Exception as e:
    print("Whoops, bot failed to connect to Discord.")
    print(e)