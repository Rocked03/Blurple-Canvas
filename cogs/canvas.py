import aiohttp, asyncio, colorsys, copy, datetime, discord, io, json, math, motor.motor_asyncio, numpy, PIL, pymongo, \
    random, sys, textwrap, time, traceback, typing
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from discord import app_commands
from bson import json_util
from PIL import Image, ImageDraw, ImageFont
from pymongo import UpdateOne, InsertOne
from pymongo.collection import Collection
from pymongo.database import Database
# pillow, motor, pymongo, discord.py, numpy

from skippersist import SkipPersist
from boardpersist import BoardPersist
from reminderpersist import ReminderPersist


def dev():
    async def pred(ctx):
        return ctx.author.id in ctx.bot.allowedusers

    return commands.check(pred)


def inteam():
    async def pred(ctx):
        # return True
        return ctx.author.id in [i.id for i in ctx.bot.blurpleguild.members]

        # a = any(elem in [v for k, v in ctx.bot.teams.items()] for elem in [i.id for i in (await ctx.bot.blurpleguild.fetch_member(ctx.author.id)).roles]) 
        # if not a: ctx.bot.cd.add(ctx.author.id)
        # return a

    return commands.check(pred)


def mod():
    async def pred(ctx): return any(elem in [v for k, v in ctx.bot.modroles.items()] for elem in
                                    [i.id for i in (await ctx.bot.blurpleguild.fetch_member(ctx.author.id)).roles])

    return commands.check(pred)


def executive():
    async def pred(ctx): return any(
        i in [ctx.bot.modroles['Admin'], ctx.bot.modroles['Executive'], ctx.bot.modroles['Exec Assist']] for i in
        [i.id for i in (await ctx.bot.blurpleguild.fetch_member(ctx.author.id)).roles])

    return commands.check(pred)


def admin():
    # async def pred(ctx): return any(elem in [v for k, v in ctx.bot.modroles.items() if k == "Admin"] for elem in [i.id for i in ctx.bot.blurpleguild.fetch_member(ctx.author.id).roles])
    async def pred(ctx): return ctx.bot.modroles['Admin'] in [i.id for i in (
        await ctx.bot.blurpleguild.fetch_member(ctx.author.id)).roles]

    return commands.check(pred)


# todo
# reload bot without breaking stuff
# individual colour info graphic things
# slash commands
# in-built leaderboard?
# local server id in history?


class dbs():
    def __init__(self, mongo_instance: motor.motor_asyncio.AsyncIOMotorClient):
        self.users = mongo_instance.users  # type: Database
        self.boards = mongo_instance.boards  # type: Database
        self.history = mongo_instance.history  # type: Database


class CanvasCog(commands.Cog, name="Canvas"):
    """Canvas Module"""

    def __init__(self, bot):
        self.bot = bot

        self.bot.initfinished = False

        self.bot.modroles = {
            "Admin": 443013283977494539,
            "Executive": 413213839866462220,
            "Exec Assist": 470272155876065280,
            "Moderator": 569015549225598976,
            "Helper": 442785212502507551,
        }

        self.bot.cd = set()

        # self.blurplehex = 0x7289da
        self.blurplehex = 0x5865F2
        # self.blurplergb = (114, 137, 218)
        self.blurplergb = (88, 101, 242)
        # self.dblurplergb = (78, 93, 148)
        self.dblurplergb = (69, 79, 191)

        # self.bot.teams = {
        #     "light": 573011450231259157,
        #     "dark": 573011441683005440,
        # }
        self.bot.teams = {"blurple user": 1082567913103425626}

        self.bot.artistrole = 1082567922779688980

        self.skippersist = SkipPersist()
        self.bot.loop.create_task(self.skippersist.c('setup'))
        self.bot.loop.create_task(self.getskips())

        self.reminderpersist = ReminderPersist()
        self.bot.loop.create_task(self.reminderpersist.c('setup'))
        self.bot.loop.create_task(self.getreminders())

        self.bot.boards = dict()

        self.bot.partnercolourlock = True

        self.bot.defaultcanvas = "Canvas"
        self.bot.ignoredcanvases = ['main2019', 'main2020', 'staff', 'example', 'big', 'canvasold', 'canvas2022',
                                    'mini']

        self.bot.dblock = asyncio.Lock()

        self.bot.pymongo = motor.motor_asyncio.AsyncIOMotorClient(
            "mongodb://localhost:27017/?retryWrites=true&w=majority")
        self.bot.pymongoog = pymongo.MongoClient("mongodb://localhost:27017/?retryWrites=true&w=majority")

        self.bot.loop.create_task(self.getboards())

        self.boardpersist = BoardPersist()
        self.bot.loop.create_task(self.boardpersist.c('setup'))
        self.bot.loop.create_task(self.getuboards())

        # self.bot.loop.create_task(reloadpymongo(self))

        self.bot.loop.create_task(self.loadcolourimg())

        self.bot.loop.create_task(self.fetchserver())

        self.bot.initfinished = True

    def loadboards(self):
        colls = self.bot.pymongoog.boards.list_collection_names()
        for name in colls:
            if name in self.bot.ignoredcanvases: continue
            print(f"Loading '{name}'...")
            board = self.bot.pymongoog.boards[name]
            # info = (board.find_one({'type': 'info'}))['info']
            # history = (board.find_one({'type': 'history'}))['history']
            # print(f"Loading data...")
            # data = list(board.find({'type': 'data'}))
            boarddata = list(board.find({'type': {'$ne': 'history'}}))
            info = next(x for x in boarddata if x['type'] == 'info')['info']
            print(info)
            data = [x for x in boarddata if x['type'] == 'data']
            print(f"Saving data...")
            d = {k: v for d in data for k, v in d.items()}
            self.bot.boards[info['name'].lower()] = self.board(name=info['name'], width=info['width'],
                                                               height=info['height'], locked=info['locked'], data=d,
                                                               last_updated=info[
                                                                   'last_updated'] if 'last_updated' in info else datetime.datetime.utcnow())

            print(f"Loaded '{name}'")

        print('All boards loaded')

    async def getboards(self):
        print('Loading boards off DB')

        self.bot.dbs = dbs(self.bot.pymongo)

        some_stuff = await self.bot.loop.run_in_executor(None, self.loadboards)

        for b in self.bot.boards.keys():
            self.bot.loop.create_task(self.backup(b))

    async def reloadpymongo(self):
        while True:
            await asyncio.sleep(300)  # 5 minutes
            self.bot.pymongo = motor.motor_asyncio.AsyncIOMotorClient(
                "mongodb://localhost:27017/?retryWrites=true&w=majority")
            self.bot.pymongoog = pymongo.MongoClient(
                "mongodb://localhost:27017/?retryWrites=true&w=majority&ssl_cert_reqs=CERT_NONE")

    async def loadcolourimg(self):
        self.bot.colourimg = {
            x: await self.bot.loop.run_in_executor(None, self.image.colours, self, x) for x in
            ['all', 'main', 'partner']
        }

    async def fetchserver(self):
        await asyncio.sleep(60)
        self.bot.blurpleguild = self.bot.get_guild(412754940885467146)

    async def getskips(self):
        self.bot.skipconfirm = await self.skippersist.c('get_all')

    async def getreminders(self):
        self.bot.cooldownreminder = await self.reminderpersist.c('get_all')

    async def getuboards(self):
        self.bot.uboards = await self.boardpersist.c('get_all_dict')

    class board():
        def __init__(self, *, name, width, height, locked, data=dict(), last_updated=datetime.datetime.utcnow()):
            self.data = data
            self.name = name
            self.width = width
            self.height = height
            self.locked = locked
            self.last_updated = last_updated

    class image():
        # font = lambda x: ImageFont.truetype("Uni Sans Heavy.otf", x)
        font = lambda x: ImageFont.truetype("GintoNord-Black.otf", x)
        fontxy = font(60)
        # fonttitle = font(18)
        fonttitle = font(16)
        # fontcoordinates = font(21)
        fontcoordinates = font(19)
        fontcolourtitle = font(120)

        def imager(self, aboard, x, y, zoom, highlight=True):
            height = zoom
            width = zoom

            if zoom < 150:
                pixelwidth = 2
                imagemax = 1500
            elif zoom < 250:
                pixelwidth = 1
                imagemax = 2000
            else:
                pixelwidth = 1
                imagemax = 3000
            borderwidth = 100

            size = (int(imagemax - (
                    (imagemax - borderwidth - pixelwidth * (width + 1)) % width)),
                    int(imagemax - ((imagemax - borderwidth - pixelwidth *
                                     (height + 1)) % height)))
            pixelsizex = (list(size)[0] - borderwidth - pixelwidth *
                          (width + 1)) / width
            pixelsizey = (list(size)[1] - borderwidth - pixelwidth *
                          (height + 1)) / height

            sizex, sizey = size

            colours = {}
            for k, v in self.bot.partners.items():
                colours[v['tag']] = v['rgb']
            for k, v in self.bot.coloursrgb.items():
                colours[k] = v

            board = Image.new('RGBA', size, (*(self.blurplergb), 255))
            draw = ImageDraw.Draw(board)
            draw.rectangle([(borderwidth + 1, borderwidth + 1), size],
                           fill=(*(self.dblurplergb), 255))

            loc, emoji, raw, zoom = self.screen(aboard, x, y, zoom)
            locx, locy = loc

            for yc, yn in zip(raw, range(zoom)):
                for xc, xn in zip(yc, range(zoom)):
                    draw.rectangle([(int(borderwidth + pixelwidth *
                                         (xn + 1) + pixelsizex * (xn)),
                                     int(borderwidth + pixelwidth *
                                         (yn + 1)) + pixelsizey * (yn)),
                                    (int(borderwidth + pixelwidth *
                                         (xn + 1) + pixelsizex * (xn + 1)),
                                     int(borderwidth + pixelwidth *
                                         (yn + 1) + pixelsizey * (yn + 1)))],
                                   fill=colours[xc])  # Pixels

            if highlight:
                draw.rectangle([
                    (int(borderwidth + pixelwidth * (locx) + pixelsizex *
                         (locx - 1)), int(borderwidth + pixelwidth *
                                          (locy)) + pixelsizey * (locy - 1)),
                    (int(borderwidth + pixelwidth * (locx) + pixelsizex * (locx)),
                     int(borderwidth + pixelwidth * (locy) + pixelsizey * (locy)))
                ],
                    fill=None,
                    outline=(255, 255, 255, 255))  # Location highlight

                draw.rectangle(
                    [(int(borderwidth + pixelwidth * (locx) + pixelsizex *
                          (locx - 1)), int(
                        round(borderwidth - (pixelsizex / 3), 0))),
                     (int(borderwidth + pixelwidth * (locx) + pixelsizex * (locx)),
                      borderwidth)],
                    fill=colours[raw[0][locx - 1]])
                draw.line(
                    ((int(borderwidth + pixelwidth * (locx) + pixelsizex *
                          (locx - 1)),
                      int(round(borderwidth - (pixelsizex / 3), 0) - 1)),
                     (int(borderwidth + pixelwidth * (locx) + pixelsizex * (locx)),
                      int(round(borderwidth - (pixelsizex / 3), 0) - 1))),
                    fill=(*(self.dblurplergb), 255),
                    width=1)  # Highlight x

                draw.rectangle([
                    (int(round(borderwidth - (pixelsizey / 3), 0)),
                     int(borderwidth + pixelwidth * (locy) + pixelsizey *
                         (locy - 1))),
                    (borderwidth,
                     int(borderwidth + pixelwidth * (locy) + pixelsizey * (locy)))
                ],
                    fill=colours[raw[locy - 1][0]])
                draw.line(
                    ((int(round(borderwidth - (pixelsizey / 3), 0) - 1)),
                     int(borderwidth + pixelwidth * (locy) + pixelsizey *
                         (locy - 1)),
                     (int(round(borderwidth - (pixelsizey / 3), 0) - 1)),
                     int(borderwidth + pixelwidth * (locy) + pixelsizey * (locy))),
                    fill=(*(self.dblurplergb), 255),
                    width=1)  # Highlight y

                tsx, tsy = self.image.fontxy.getsize(f"{x}  =  x")
                draw.text((sizex - tsx - ((borderwidth - tsy) / 2),
                           (borderwidth - tsy) / 2),
                          f"{x}  =  x",
                          font=self.image.fontxy,
                          fill=(185, 196, 237, 255))

                tsx, tsy = self.image.fontxy.getsize(f"y  =  {y}")
                txt = Image.new('RGBA', (tsx, tsy))
                ImageDraw.Draw(txt).text((0, 0),
                                         f"y  =  {y}",
                                         font=self.image.fontxy,
                                         fill=(185, 196, 237, 255))
                ftxt = txt.rotate(90, expand=1)
                board.paste(
                    ftxt,
                    box=(int((borderwidth - tsy) / 2),
                         int(sizey - tsx - ((borderwidth - tsy) / 2))),
                    mask=ftxt)

            spacing = 30
            tsx, tsy = draw.textsize("Project", font=self.image.fonttitle)
            draw.text((int(round(((borderwidth - tsx) / 2), 0)),
                       int((borderwidth / 2) - tsy - (spacing / 2))),
                      "Project",
                      font=self.image.fonttitle,
                      fill=(185, 196, 237, 255))
            tsx, tsy = draw.textsize("Blurple", font=self.image.fonttitle)
            draw.text((int(round(((borderwidth - tsx) / 2), 0)),
                       int((borderwidth / 2) + (spacing / 2))),
                      "Blurple",
                      font=self.image.fonttitle,
                      fill=(185, 196, 237, 255))

            if highlight:
                tsx, tsy = draw.textsize(
                    f"({x}, {y})", font=self.image.fontcoordinates)
                draw.text((int(round(((borderwidth - tsx) / 2), 0)),
                           int(round(((borderwidth - tsy) / 2), 0))),
                          f"({x}, {y})",
                          font=self.image.fontcoordinates,
                          fill=(255, 255, 255, 255))
            else:
                tsx, tsy = draw.textsize(
                    f"{aboard.name}", font=self.image.fontcoordinates)
                draw.text((int(round(((borderwidth - tsx) / 2), 0)),
                           int(round(((borderwidth - tsy) / 2), 0))),
                          f"{aboard.name}",
                          font=self.image.fontcoordinates,
                          fill=(255, 255, 255, 255))

            image_file_object = io.BytesIO()
            board.save(image_file_object, format='png')
            image_file_object.seek(0)

            return image_file_object

        def colours(self, palettes='all'):
            squaresize = 300
            borderwidth = 100
            textspacing = 200
            squaren = {
                'all': 8,
                'main': 6,
                'partner': 6
            }[palettes]

            # namefont = self.image.font(int(round(squaresize / 6.5, 0)))
            # codefont = self.image.font(int(round(squaresize / 9, 0)))
            namefont = self.image.font(int(round(squaresize / 8.5, 0)))
            codefont = self.image.font(int(round(squaresize / 10.5, 0)))

            basecorners = 50
            squarecorners = 50

            namewidth = 10

            def hsl(x):
                if len(x) > 3: x = x[:3]
                to_float = lambda x: x / 255.0
                (r, g, b) = map(to_float, x)
                h, s, l = colorsys.rgb_to_hsv(r, g, b)
                h = h if 0 < h else 1  # 0 -> 1
                return h, s, l

            rainbow = lambda x: {k: v for k, v in sorted(x.items(), key=lambda kv: hsl(kv[1]['rgb']))}

            shuffle = lambda x: {k: v for k, v in sorted(x.items(), key=lambda kv: random.randint(1, 99999999))}

            allcolours = {}

            if palettes in ['all', 'main']:
                allcolours['Main Colours'] = rainbow(
                    {k: v for k, v in self.bot.coloursdict.items() if k not in ['Edit tile', 'Blank tile']})
            if palettes in ['all', 'partner']:
                allcolours['Partner Colours'] = rainbow(self.bot.partners)

            height = 2 * borderwidth
            for i in allcolours.values():
                height += textspacing
                height += squaresize * math.ceil(len(i) / squaren)
            height += borderwidth * (len(allcolours) - 1)

            width = 2 * borderwidth + squaren * squaresize

            # img = Image.new('RGBA', (width, height), (*(self.blurplergb), 127))
            img = self.image.round_rectangle(self, (width, height), basecorners, (*(self.blurplergb), 75),
                                             allcorners=True)
            draw = ImageDraw.Draw(img)

            space = 0
            for name, cs in allcolours.items():
                bg = self.image.round_rectangle(self,
                                                (squaren * squaresize,
                                                 textspacing + squaresize * math.ceil(len(cs) / squaren)),
                                                squarecorners, (*(self.dblurplergb), 255), allcorners=True
                                                )
                img.paste(bg, (borderwidth, borderwidth + space), bg)

                tsx, tsy = draw.textsize(name, font=self.image.fontcolourtitle)

                draw.text((int(round(((width - tsx) / 2), 0)),
                           int(round(((textspacing - tsy) / 2 + space + borderwidth), 0))),
                          name,
                          font=self.image.fontcolourtitle,
                          fill=(255, 255, 255, 255))

                # rows = [[] for i in range(math.ceil(len(i) / squaren))]
                rows = [[] for i in range(math.ceil(len(cs) / squaren))]
                for n, (k, c) in enumerate(cs.items()):
                    rows[math.floor(n / squaren)].append(c)
                if not rows[-1]: rows.pop(len(rows) - 1)

                def roundrect(img, colour, coords, corners):
                    a = self.image.round_rectangle(
                        self, (squaresize, squaresize), squarecorners, colour,
                        topleft=corners['tl'], topright=corners['tr'], bottomleft=corners['bl'],
                        bottomright=corners['br']
                    )
                    img.paste(a, coords, a)
                    return img

                for rown, row in enumerate(rows):
                    for pos, cdict in enumerate(row):
                        xpos = borderwidth + pos * squaresize  # + (squaren - len(row)) * squaresize / 2
                        ypos = space + borderwidth + textspacing + rown * squaresize

                        roundcorners = {
                            'tl': rown == 0 and pos == 0,
                            'tr': rown == 0 and pos == squaren - 1,
                            'bl': rown == len(rows) - 1 and pos == 0,
                            'br': rown == len(rows) - 1 and pos == squaren - 1
                        }

                        if any(list(roundcorners.values())):
                            img = roundrect(img, cdict['rgb'], (xpos, ypos), roundcorners)
                        else:
                            draw.rectangle([
                                (xpos, ypos),
                                (xpos + squaresize - 1, ypos + squaresize - 1)
                            ],
                                fill=cdict['rgb']
                            )

                        tcolour = (0, 0, 0, 255) if hsl(cdict['rgb'])[2] == 1 else (255, 255, 255, 255)

                        cname = '\n'.join(textwrap.wrap(cdict['name'], width=namewidth))
                        tsnx, tsny = draw.textsize(cname, font=namefont)
                        draw.multiline_text(
                            (
                                int(round(xpos + (squaresize - tsnx) / 2, 0)),
                                int(round(ypos + (squaresize - tsny) / 2, 0))
                            ),
                            cname,
                            font=namefont,
                            fill=tcolour,
                            align='center',
                            spacing=int(round(squaresize / 30))

                        )

                        rgbtxt = ', '.join([str(i) for i in cdict['rgb'][:3]])
                        tsnx, tsny = draw.textsize(rgbtxt, font=codefont)
                        draw.text(
                            (
                                int(round(xpos + (squaresize - tsnx) / 2, 0)),
                                int(round(ypos + squaresize / 10, 0))
                            ),
                            rgbtxt,
                            font=codefont,
                            fill=tcolour,
                        )

                        tsnx, tsny = draw.textsize(cdict['tag'], font=codefont)
                        draw.text(
                            (
                                int(round(xpos + (squaresize - tsnx) / 2, 0)),
                                int(round(ypos + (squaresize - tsny) - squaresize / 10, 0))
                            ),
                            cdict['tag'],
                            font=codefont,
                            fill=tcolour,
                        )

                space += textspacing + squaresize * math.ceil(len(cs) / squaren) + borderwidth

            image_file_object = io.BytesIO()
            img.save(image_file_object, format='png')
            image_file_object.seek(0)

            return image_file_object

        def round_corner(self, radius, fill):
            """Draw a round corner"""
            corner = Image.new('RGBA', (radius, radius), (0, 0, 0, 0))
            draw = ImageDraw.Draw(corner)
            draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=fill)
            return corner

        def round_rectangle(self, size, radius, fill, topleft=False, topright=False, bottomleft=False,
                            bottomright=False, allcorners=False):
            """Draw a rounded rectangle"""
            if allcorners: topleft = topright = bottomleft = bottomright = True

            width, height = size
            rectangle = Image.new('RGBA', size, fill)
            corner = self.image.round_corner(self, radius, fill)
            if topleft: rectangle.paste(corner, (0, 0))
            if bottomleft: rectangle.paste(corner.rotate(90), (0, height - radius))  # Rotate the corner and paste it
            if bottomright: rectangle.paste(corner.rotate(180), (width - radius, height - radius))
            if topright: rectangle.paste(corner.rotate(270), (width - radius, 0))
            return rectangle

    class coordinates(commands.Converter):
        def __init__(self, colour: bool = False):
            self.colour = colour

        async def convert(self, ctx, argument):
            try:
                arg = argument.split()

                if len(arg) < 3:
                    zoom = None
                else:
                    if self.colour and len(arg) == 3:
                        zoom = None
                    else:
                        zoom = int(arg[2])

                if self.colour: colour = arg[-1]

                x = int(arg[0].replace('(', '').replace(',', ''))
                y = int(arg[1].replace(')', ''))
            except Exception as e:
                x, y, zoom, colour = (0, 0, None, None)

            if self.colour:
                return (x, y, zoom, colour)
            else:
                return (x, y, zoom)

    async def cog_check(self, ctx):
        return ctx.guild.id in [self.bot.blurpleguild.id] + [int(i['guild']) for i in self.bot.partners.values()]

    @commands.Cog.listener()  # Error Handler
    async def on_command_error(self, ctx, error):
        ignored = (
            commands.CommandNotFound, commands.UserInputError, asyncio.TimeoutError, asyncio.exceptions.TimeoutError)
        if isinstance(error, ignored): return

        if isinstance(error, commands.CheckFailure):
            # print(error)
            # await ctx.reply(f"It doesn't look like you are allowed to run this command. Make sure you've got the Blurple User role in the main server, otherwise these commands will not work!")
            await ctx.reply(
                f"It doesn't look like you are allowed to run this command. Make sure you're in the host Project Blurple server, otherwise these commands will not work!")
            return

        if isinstance(error, commands.CommandOnCooldown):
            if any(i in [706475186274172989, 803595727175155723] for i in [role.id for role in ctx.author.roles]):
                if ctx.author.id in self.bot.cd:
                    self.bot.cd.remove(ctx.author.id)
                await ctx.reinvoke()
                return

            seconds = error.retry_after
            seconds = round(seconds, 2)
            hours, remainder = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remainder, 60)

            if ctx.command.name == "place":
                if ctx.author.id in self.bot.cd:
                    self.bot.cd.remove(ctx.author.id)
                    await ctx.reinvoke()
                    return

            if minutes:
                await ctx.reply(
                    f"This command is on cooldown ({minutes}m, {seconds}s)"
                )
            else:
                await ctx.reply(
                    f"This command is on cooldown ({seconds}s)"
                )
            return

        if isinstance(error, discord.Forbidden):
            await ctx.reply(
                f"I don't seem to have the right permissions to do that. Please check with the mods of this server that I have Embed Links // Send Images // Manage Message (for clearing reactions) perms!"
            )

        traceback.print_exception(
            type(error), error, error.__traceback__, file=sys.stderr)

    def screen(self, board, x: int, y: int, zoom: int = 7):
        tl = math.ceil(zoom / 2) - 1
        # tly = (y / 2) - 1 if y % 2 == 0 else (y / 2) - 0.5
        tlx = x - tl
        tly = y - tl

        locx = (zoom / 2) if zoom % 2 == 0 else (zoom / 2) + 0.5
        locy = locx

        if x < zoom / 2:
            tlx = 1
            locx = x
        elif x > board.width - zoom / 2:
            tlx = board.width - zoom + 1
            locx = zoom - (board.width - x)

        if y < zoom / 2:
            tly = 1
            locy = y
        elif y > board.height - zoom / 2:
            tly = board.height - zoom + 1
            locy = zoom - (board.height - y)

        loc = (int(locx), int(locy))

        demoji = [[] for i in range(zoom)]
        draw = [[] for i in range(zoom)]
        pt = {}
        for k, v in self.bot.partners.items():
            pt[v['tag']] = v['emoji']
        for k, v in self.bot.colours.items():
            pt[k] = v

        for yn, xs in board.data.items():
            if not yn.isdigit(): continue
            if tly <= int(yn) < tly + zoom:
                de = []
                dr = []
                for xn, pixel in xs.items():
                    if tlx <= int(xn) < tlx + zoom:
                        # de.append("<:" + pt[pixel["c"]] + ">")
                        # dr.append(pixel["c"])
                        de.append("<:" + pt[pixel] + ">")
                        dr.append(pixel)
                if dr:
                    demoji[int(yn) - tly] = de
                    draw[int(yn) - tly] = dr

        return loc, demoji, draw, zoom

    class boardspec(commands.Converter):
        async def convert(self, ctx, seed):
            options = ['random']
            if seed.lower() in [i.lower() for i in options]:
                return seed.lower()
            else:
                raise Exception

    async def update_history(self, board, colour, author, coords):
        time = datetime.datetime.utcnow()
        board_history = self.bot.dbs.history[board.name.lower()]  # type: Collection
        board_history.insert_one({'colour': colour, 'author': author, 'coords': coords, 'created': time})
        board.last_updated = time

    async def backup(self, boardname):
        n = 1
        nbackups = 4
        period = 300  # seconds // 5 minutes
        while True:
            await asyncio.sleep(period)
            await self.dobackup(boardname, n)
            n = n + 1 if n < nbackups else 1

    async def dobackup(self, boardname, n):
        try:
            print(f"Starting backup of {boardname}_{n}")
            async with aiohttp.ClientSession() as session:
                with open(f'backups/backup_{boardname}_{n}.json', 'wt') as f:
                    data = {i: getattr(self.bot.boards[boardname], i) for i in
                            ['data', 'name', 'width', 'height', 'locked', 'last_updated']}
                    try:
                        data['data'].pop('_id')
                    except KeyError:
                        pass
                    json.dump(data, f, default=json_util.default)

            print(f"Saved backup {boardname}_{n}   {datetime.datetime.utcnow()}")
        except Exception as e:
            print(e)

    @commands.command()
    @admin()
    async def loadbackup(self, ctx, n: int, boardname):
        async with aiohttp.ClientSession() as session:
            with open(f'backups/backup_{boardname}_{n}.json', 'rt') as f:
                data = json.load(f, object_hook=json_util.object_hook)
            board = self.board(**data)

        async with aiohttp.ClientSession() as session:
            async with ctx.typing():
                start = time.time()
                x, y, zoom = (1, 1, board.width)
                image = await self.bot.loop.run_in_executor(
                    None, self.image.imager, self, board, x, y, zoom, False)
                end = time.time()
                image = discord.File(fp=image, filename=f'board_{x}-{y}.png')

                embed = discord.Embed(
                    colour=self.blurplehex, timestamp=discord.utils.utcnow())
                embed.set_author(name=f"{board.name} | Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                await ctx.reply(embed=embed, file=image)

        await ctx.reply("Is this what you're looking for?")

        def check(message):
            return ctx.author == message.author and message.content.lower() in ['yes', 'no', 'y',
                                                                                'n'] and message.channel == ctx.message.channel

        msg = await self.bot.wait_for('message', check=check)

        if msg.content in ['no', 'n']:
            return await msg.reply("Ok, cancelled")

        await msg.reply("Ok, pushing to db - please make sure the board exists so I can update it")

        t1 = time.time()

        newboard = board

        self.bot.boards[boardname] = newboard

        await ctx.send('Writing to db')
        print('Writing to db')

        dboard = self.bot.dbs.boards.get_collection(newboard.name.lower())  # type: Collection
        dboard.bulk_write([
            UpdateOne({'type': 'info'}, {'$set': {
                'info': {'name': newboard.name, 'width': newboard.width, 'height': newboard.height, 'locked': False,
                         'last_updated': newboard.last_updated}}}),
        ])

        print('Info done')
        await ctx.send('Info done')

        board_history = self.bot.dbs.history[newboard.name.lower()]  # type: Collection
        board_history.delete_many({'created': {'$gt': newboard.last_updated}})

        print('History done')
        await ctx.send('History done')

        await self.bot.dbs.boards[board.name.lower()].bulk_write(
            [UpdateOne({'row': y + 1}, {'$set': {str(y + 1): newboard.data[str(y + 1)]}}) for y in
             range(newboard.height)])

        t2 = time.time()

        print('Board saved')
        await msg.reply(f"Board saved ({round((t2 - t1), 4)}s)")

    @commands.command()
    @admin()
    async def forcebackup(self, ctx, boardname):
        await self.dobackup(boardname, 0)
        await ctx.reply("Done")

    @commands.command(aliases=['unlockboard'])
    @admin()
    async def lockboard(self, ctx, boardname: str):
        if boardname.lower() not in self.bot.boards.keys():
            return await ctx.reply(
                f'That is not a valid board. To see all valid boards, type `{ctx.prefix}boards`.'
            )
        board = self.bot.boards[boardname.lower()]

        current = board.locked

        await self.bot.dbs.board[board.name.lower()].update_one({'type': 'info'},
                                                                {'$set': {'info.locked': not current}})

        board.locked = not current

        await ctx.reply(f"Set **{board.name}** locked state to `{not current}`")

    @commands.command(aliases=['showpixelhistory', 'sph'])
    @mod()
    async def show_pixel_history(self, ctx: commands.Context, boardname: str, x: int, y: int):

        if boardname.lower() not in self.bot.boards.keys():
            return await ctx.reply(
                f'That is not a valid board. To see all valid boards, type `{ctx.prefix}boards`.'
            )
        board = self.bot.boards[boardname.lower()]
        if x < 1 or x > board.width or y < 1 or y > board.height:
            return await ctx.reply(
                f'Please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )

        history = self.bot.dbs.history[boardname.lower()]  # type: Collection
        resp = history.find({'coords': (x, y)})
        resp.sort('created', pymongo.DESCENDING)
        message = f"History for Pixel ({x}, {y}) on {boardname}:"
        counter = 1
        async for r in resp:
            try:
                user = self.bot.get_user(r['author']) or await self.bot.fetch_user(r['author'])
                user_str = f"{user.mention} (`{r['author']}`)"
            except Exception:
                user_str = r['author']
            message += f"\n{counter}. {user_str} placed {r['colour']} at {r['created'].strftime('%m/%d/%Y, %H:%M:%S')} UTC"
            counter += 1
            if counter >= 10:
                break

        await ctx.reply(message)

    @commands.command(aliases=['showuserhistory', 'suh'])
    @mod()
    async def show_user_history(self, ctx: commands.Context, boardname: str, user):

        if boardname.lower() not in self.bot.boards.keys():
            return await ctx.reply(
                f'That is not a valid board. To see all valid boards, type `{ctx.prefix}boards`.'
            )
        try:
            user = self.bot.get_user(user) or await self.bot.fetch_user(user)
        except Exception:
            return await ctx.reply(f'User is not found.')

        board = self.bot.boards[boardname.lower()]

        history = self.bot.dbs.history[boardname.lower()]  # type: Collection
        resp = history.find({'author': user.id})
        resp.sort('created', pymongo.DESCENDING)
        message = f"History for User {user.mention} (`{user.id}`) on {boardname}:"
        counter = 1
        async for r in resp:
            message += f"\n{counter}. Placed {r['colour']} on ({r['coords'][0]}, {r['coords'][1]}) at {r['created'].strftime('%m/%d/%Y, %H:%M:%S')} UTC"
            counter += 1
            if counter >= 10:
                break

        await ctx.reply(message)

    @commands.command(name="createboard", aliases=["cb"])
    @admin()
    async def createboard(self, ctx, x: int, y: int, seed: typing.Optional[boardspec] = None, *, name: str):
        """Creates a board. Optional seed parameter. Must specify width (x), height (y), and name."""
        if not self.bot.initfinished: return await ctx.reply(
            'Please wait for the bot to finish retrieving boards from database.')

        if any(i < 5 for i in [x, y]):
            return await ctx.reply("Please have a minimum of 5.")

        await ctx.reply("Creating board...")

        fill = "blank"

        try:
            self.bot.boards[name.lower()]
        except Exception:
            pass
        else:
            return await ctx.reply("There's already a board with that name!")

        t1 = time.time()

        self.bot.boards[name.lower()] = self.board(
            name=name, width=x, height=y, locked=False)
        newboard = self.bot.boards[name.lower()]

        for yn in range(1, y + 1):
            newboard.data[str(yn)] = {}
            for xn in range(1, x + 1):
                if seed == "random":
                    colour = random.choice([
                        name for name in self.bot.colours.keys()
                        if name not in ['edit', 'blank']
                    ])
                    # newboard.data[str(yn)][str(xn)] = {
                    #     "c": colour,
                    #     # "info": [{
                    #     #     "user": "Automatic",
                    #     #     "time": datetime.datetime.utcnow()
                    #     # }]
                    # }
                    newboard.data[str(yn)][str(xn)] = colour

                else:
                    # newboard.data[str(yn)][str(xn)] = {
                    #     "c": "blank",
                    #     # "info": [{
                    #     #     "user": "Automatic",
                    #     #     "time": datetime.datetime.utcnow()
                    #     # }]
                    # }
                    colour = "blank"
                    newboard.data[str(yn)][str(xn)] = colour

                # newboard.history[datetime.datetime.utcnow().timestamp()] = [colour, "Automatic"]
                async with self.bot.dblock:
                    await self.update_history(newboard, colour, "Automatic", (xn, yn))

        await ctx.reply("Created board, saving to database")

        await self.bot.dbs.boards.create_collection(newboard.name.lower())
        dboard = self.bot.dbs.boards.get_collection(newboard.name.lower())
        await dboard.insert_many([
            {'type': 'info',
             'info': {'name': newboard.name, 'width': newboard.width, 'height': newboard.height, 'locked': False,
                      'last_updated': newboard.last_updated}},
        ])

        self.bot.dbs.history[newboard.name.lower()]  # type: Collection

        limit = 200000
        n = newboard.width * newboard.height
        cdata = newboard.data
        datalist = []
        cline = 1
        while n > limit:
            ndata = []
            lines = math.floor(limit / newboard.width)
            # print(lines)
            for i in range(lines):
                try:
                    ndata.append({str(cline): newboard.data[str(cline)], 'type': 'data', 'row': cline})
                except KeyError:
                    pass
                cline += 1
            datalist.append(ndata)

            n -= lines * newboard.width

        # print(n / newboard.width)
        ndata = []
        for i in range(n):
            try:
                ndata.append({str(cline): newboard.data[str(cline)], 'type': 'data', 'row': cline})
            except KeyError:
                pass
            cline += 1
        datalist.append(ndata)

        for x, item in enumerate(datalist):
            await dboard.insert_many(item)
            await ctx.send(f'Saved chunk {x + 1} of {len(datalist)}')

        t2 = time.time()

        await ctx.reply(f"Board created ({round((t2 - t1), 4)}s)")

    @commands.command()
    @inteam()
    async def boards(self, ctx):
        """Lists all available canvas boards"""
        await ctx.reply(f'Boards ({len(self.bot.boards)}) - ' + ' | '.join(self.bot.boards.keys()))

    @commands.command()
    @inteam()
    async def join(self, ctx, *, name: str = None):
        """Joins a board. You need to have joined a board to start interacting with the canvas."""
        if not name: return await ctx.reply(
            f'Please specify a board to join. To see all valid boards, type `{ctx.prefix}boards`.')

        if name.lower() not in self.bot.boards.keys():
            return await ctx.reply(
                f'That is not a valid board. To see all valid boards, type `{ctx.prefix}boards`.'
            )

        self.bot.uboards[ctx.author.id] = name.lower()
        await self.boardpersist.c('update', ctx.author.id, name.lower())

        bname = self.bot.boards[name.lower()].name
        await ctx.reply(f"Joined '{bname}' board")

    @commands.command()
    @inteam()
    async def leave(self, ctx):
        """Leaves the board you've currently joined."""
        if ctx.author.id not in self.bot.uboards.keys():
            return await ctx.reply("You can't leave a board when you haven't joined one!")

        bname = self.bot.uboards[ctx.author.id]
        self.bot.uboards.pop(ctx.author.id)
        await self.boardpersist.c('update', ctx.author.id, False)

        await ctx.reply(f"Left '{bname}' board")

    async def findboard(self, ctx) -> board:
        try:
            self.bot.boards[self.bot.uboards[ctx.author.id]]
        except KeyError:
            if self.bot.defaultcanvas.lower() in [i.lower() for i in self.bot.boards.keys()]:
                self.bot.uboards[ctx.author.id] = self.bot.defaultcanvas.lower()
                await self.boardpersist.c('update', ctx.author.id, self.bot.defaultcanvas.lower())
                await ctx.reply(
                    f"You weren't added to a board, so I've automatically added you to the default '{self.bot.defaultcanvas}' board. To see all available boards, type `{ctx.prefix}boards`")
            else:
                if ctx.author.id in self.bot.uboards.keys(): self.bot.uboards.pop(ctx.author.id)
                await self.boardpersist.c('update', ctx.author.id, False)
                await ctx.reply(
                    f"You haven't joined a board! Type `{ctx.prefix}join <board>` to join a board! To see all boards, type `{ctx.prefix}boards`"
                )
                return False

        return self.bot.boards[self.bot.uboards[ctx.author.id]]  # type: CanvasCog.board

    @commands.command(name="toggleskip", aliases=["ts"])
    @inteam()
    async def toggleskip(self, ctx):
        """Toggles p/place coordinate confirmation"""
        await self.skippersist.c('toggle', ctx.author.id)
        if ctx.author.id in self.bot.skipconfirm:
            self.bot.skipconfirm.remove(ctx.author.id)
            await ctx.reply(f"Re-enabled confirmation message for {ctx.author.mention}")
        else:
            self.bot.skipconfirm.append(ctx.author.id)
            await ctx.reply(f"Disabled confirmation message for {ctx.author.mention}")

    @commands.command(name="toggleremind", aliases=["tr"])
    @inteam()
    async def toggleremind(self, ctx):
        """Toggles p/place cooldown reminder"""
        await self.reminderpersist.c('toggle', ctx.author.id)
        if ctx.author.id in self.bot.cooldownreminder:
            self.bot.cooldownreminder.remove(ctx.author.id)
            await ctx.reply(f"Disabled cooldown reminder for {ctx.author.mention}")
        else:
            self.bot.cooldownreminder.append(ctx.author.id)
            await ctx.reply(f"Enabled cooldown reminder for {ctx.author.mention}")

    @app_commands.command(name="toggleskip")
    async def slash_toggleskip(self, interaction: discord.Interaction) -> None:
        """Toggles p/place coordinate confirmation"""
        await self.skippersist.c('toggle', interaction.user.id)
        if interaction.user.id in self.bot.skipconfirm:
            self.bot.skipconfirm.remove(interaction.user.id)
            await interaction.response.send_message(f"Re-enabled confirmation message.", ephemeral=True)
        else:
            self.bot.skipconfirm.append(interaction.user.id)
            await interaction.response.send_message(f"Disabled confirmation message.", ephemeral=True)

    @app_commands.command(name="togglereminder")
    async def slash_togglereminder(self, interaction: discord.Interaction) -> None:
        """Toggles p/place cooldown reminder"""
        await self.reminderpersist.c('toggle', interaction.user.id)
        if interaction.user.id in self.bot.cooldownreminder:
            self.bot.cooldownreminder.remove(interaction.user.id)
            await interaction.response.send_message(f"Disabled cooldown reminder.", ephemeral=True)
        else:
            self.bot.cooldownreminder.append(interaction.user.id)
            await interaction.response.send_message(f"Enabled cooldown reminder.", ephemeral=True)

    @commands.command(name="view", aliases=["see"])
    @commands.cooldown(1, 10, BucketType.user)
    @inteam()
    async def view(self, ctx, *, xyz: coordinates = None):
        """Views a section of the board as an image. Must have xy coordinates, zoom (no. of tiles wide) optional."""
        board = await self.findboard(ctx)
        if not board: return

        # if not xyz: return await ctx.reply(f'Please specify coordinates (e.g. `234 837` or `12 53`)')

        if xyz:
            x, y, zoom = xyz

            if board.data == None:
                return await ctx.reply('There is currently no board created')

            if x < 1 or x > board.width or y < 1 or y > board.height:
                return await ctx.reply(
                    f'Please send coordinates between (1, 1) and ({board.width}, {board.height})'
                )

            defaultzoom = 25

            if zoom == None or zoom > board.width or zoom > board.height:
                zoom = defaultzoom
            if zoom > board.width or zoom > board.height:
                if board.width > board.height:
                    zoom = board.width
                else:
                    zoom = board.height
            if zoom < 5:
                return await ctx.reply(f'Please have a minumum zoom of 5 tiles')
        else:
            x, y, zoom = (1, 1, board.width)

        async with aiohttp.ClientSession() as session:
            async with ctx.typing():
                start = time.time()
                image = await self.bot.loop.run_in_executor(
                    None, self.image.imager, self, board, x, y, zoom, bool(xyz))
                end = time.time()
                image = discord.File(fp=image, filename=f'board_{x}-{y}.png')

                embed = discord.Embed(
                    colour=self.blurplehex, timestamp=discord.utils.utcnow())
                embed.set_author(name=f"{board.name} | Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                await ctx.reply(embed=embed, file=image)

    @commands.command(name="viewnav", aliases=["seenav"])
    @commands.cooldown(1, 30, BucketType.user)
    @inteam()
    async def viewnav(self, ctx, *, xyz: coordinates = None):
        """Views a section of the boards as an inline image created with emojis. Can be navigatable via interactive input. Must have xy coordinates."""
        board = await self.findboard(ctx)
        if not board: return

        if not xyz: return await ctx.reply(f'Please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom = xyz

        if board.data == None:
            return await ctx.reply('There is currently no board created')

        if x < 1 or x > board.width or y < 1 or y > board.height:
            return await ctx.reply(
                f'Please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )

        loc, emoji, raw, zoom = self.screen(board, x, y, 7)
        locx, locy = loc
        # emoji[locx - 1][locy - 1] = "<:" + self.bot.colours["edit"] + ">"

        display = f"**Blurple Canvas - ({x}, {y})**\n"

        if locy - 2 >= 0: emoji[locy - 2].append(" ⬆")
        emoji[locy - 1].append(f" **{y}** (y)")
        if locy < zoom: emoji[locy].append(" ⬇")

        display += "\n".join(["".join(i) for i in emoji]) + "\n"

        if locx - 2 < 0:
            display += (self.bot.empty * (locx - 2)) + f" **{x}** (x) ➡"
        elif locx > zoom - 1:
            display += (self.bot.empty * (locx - 2)) + f"⬅ **{x}** (x)"
        else:
            display += (self.bot.empty * (locx - 2)) + f"⬅ **{x}** (x) ➡"

        embed = discord.Embed(
            colour=self.blurplehex, timestamp=discord.utils.utcnow())
        # embed.add_field(name = "Board", value = display)
        embed.set_footer(
            text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
            icon_url=self.bot.user.avatar)
        embed.set_author(name=board.name)
        msg = await ctx.reply(display, embed=embed)

        # arrows = ["⬅", "⬆", "⬇", "➡"]
        # for emote in arrows:
        #     await msg.add_reaction(emote)

        # def check(payload):
        #     return payload.user_id == ctx.author.id and payload.message_id == msg.id and str(
        #         payload.emoji) in arrows

        while True:
            # done, pending = await asyncio.wait(
            #     [
            #         self.bot.wait_for(
            #             'raw_reaction_add', timeout=30.0, check=check),
            #         self.bot.wait_for(
            #             'raw_reaction_remove', timeout=30.0, check=check)
            #     ],
            #     return_when=asyncio.FIRST_COMPLETED)

            # try:
            #     stuff = done.pop().result()
            # except asyncio.TimeoutError:
            #     await msg.clear_reactions()
            #     for future in done:
            #         future.exception()
            #     for future in pending:
            #         future.cancel()
            #     return
            # for future in done:
            #     future.exception()
            # for future in pending:
            #     future.cancel()

            # payload = stuff

            # emojiname = str(payload.emoji)
            # if emojiname == "⬅" and x > 1: x -= 1
            # elif emojiname == "➡" and x < board.width: x += 1
            # elif emojiname == "⬇" and y < board.height: y += 1
            # elif emojiname == "⬆" and y > 1: y -= 1

            view = NavigateView(ctx.author.id)
            [i for i in view.children if i.custom_id == "cancel"][0].disabled = True
            await msg.edit(view=view)

            timeout = await view.wait()

            if timeout:
                await msg.edit(view=None)
                return

            if view.confirm == True:
                break

            if view.value == "L" and x > 1:
                x -= 1
            elif view.value == "R" and x < board.width:
                x += 1
            elif view.value == "D" and y < board.height:
                y += 1
            elif view.value == "U" and y > 1:
                y -= 1

            loc, emoji, raw, zoom = self.screen(board, x, y, 7)

            locx, locy = loc

            display = f"**Blurple Canvas - ({x}, {y})**\n"

            if locy - 2 >= 0: emoji[locy - 2].append(" ⬆")
            emoji[locy - 1].append(f" **{y}** (y)")
            if locy < zoom: emoji[locy].append(" ⬇")

            display += "\n".join(["".join(i) for i in emoji]) + "\n"

            if locx - 2 < 0:
                display += (self.bot.empty * (locx - 2)) + f" **{x}** (x) ➡"
            elif locx > zoom - 1:
                display += (self.bot.empty * (locx - 2)) + f"⬅ **{x}** (x)"
            else:
                display += (self.bot.empty * (locx - 2)) + f"⬅ **{x}** (x) ➡"

            # display = "\n".join(["".join(i) for i in emoji])
            # print(display)
            # embed.set_field_at(0, name = "Board", value = display)
            # await msg.edit(embed=embed)
            await msg.edit(content=display)

        await msg.edit(view=None)

    @commands.command(hidden=True)
    @dev()
    async def viewnavexp(self, ctx, *, xyz: coordinates = None):
        board = await self.findboard(ctx)
        if not board: return

        if not xyz: return await ctx.reply('Please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom = xyz

        if x < 1 or x > board.width or y < 1 or y > board.height:
            return await ctx.reply(
                f'Please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )

        if zoom == None:
            if board.width > board.height:
                zoom = board.width
            else:
                zoom = board.height
        if zoom > board.width or zoom > board.height:
            if board.width > board.height:
                zoom = board.width
            else:
                zoom = board.height
        if zoom < 5:
            return await ctx.reply(f'Please have a minumum zoom of 5 tiles')

        async with aiohttp.ClientSession() as session:
            async with ctx.typing():
                start = time.time()
                image = await self.bot.loop.run_in_executor(
                    None, self.image.imager, self, board, x, y, zoom)
                end = time.time()
                image = discord.File(fp=image, filename=f'board_{x}-{y}.png')

                embed = discord.Embed(
                    colour=self.blurplehex, timestamp=discord.utils.utcnow())
                embed.set_author(name=f"Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                msg = await ctx.reply(embed=embed, file=image)

        arrows = ["⬅", "⬆", "⬇", "➡"]
        for emote in arrows:
            await msg.add_reaction(emote)

        def check(payload):
            return payload.user_id == ctx.author.id and payload.message_id == msg.id and str(
                payload.emoji) in arrows

        while True:
            done, pending = await asyncio.wait(
                [
                    self.bot.wait_for(
                        'raw_reaction_add', timeout=30.0, check=check),
                    self.bot.wait_for(
                        'raw_reaction_remove', timeout=30.0, check=check)
                ],
                return_when=asyncio.FIRST_COMPLETED)

            try:
                stuff = done.pop().result()
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                return
            for future in done:
                future.exception()
            for future in pending:
                future.cancel()

            payload = stuff

            emojiname = str(payload.emoji)
            if emojiname == "⬅" and x > 1:
                x -= 1
            elif emojiname == "➡" and x < board.width:
                x += 1
            elif emojiname == "⬇" and y < board.height:
                y += 1
            elif emojiname == "⬆" and y > 1:
                y -= 1

            async with aiohttp.ClientSession() as session:
                async with ctx.typing():
                    start = time.time()
                    image = await self.bot.loop.run_in_executor(
                        None, self.image.imager, self, board, x, y, zoom)
                    end = time.time()
                    image = discord.File(
                        fp=image, filename=f'board_{x}-{y}.png')

                    embed.set_author(
                        name=f"Image took {end - start:.2f}s to load")
                    embed.set_image(url=f"attachment://board_{x}-{y}.png")
                    await msg.edit(embed=embed, file=image)

    @commands.command(name="place", aliases=["p"])
    @inteam()
    @commands.cooldown(1, 30, BucketType.user)  # 1 msg per 30s
    async def place(self, ctx, *, xyz: coordinates(True) = None):
        """Places a tile at specified location. Must have xy coordinates. Same inline output as viewnav. Choice to reposition edited tile before selecting colour. Cooldown of 30 seconds per tile placed."""
        cdexpiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=30)

        board = await self.findboard(ctx)
        if not board:
            return self.bot.cd.add(ctx.author.id)

        if board.locked == True:
            return await ctx.reply(f'This board is locked (view only)')

        if ctx.author in self.bot.cd: self.bot.cd.remove(ctx.author.id)

        if not board:
            self.bot.cd.add(ctx.author.id)
            return

        if not xyz:
            self.bot.cd.add(ctx.author.id)
            return await ctx.reply(f'Please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom, colour = xyz

        if board.data == None:
            await ctx.reply('There is currently no board created')
            self.bot.cd.add(ctx.author.id)
            return

        if x < 1 or x > board.width or y < 1 or y > board.height:
            self.bot.cd.add(ctx.author.id)
            await ctx.reply(
                f'Please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )
            return

        success = False

        if colour.lower() == 'blnk': colour = 'blank'
        if colour.lower() in [i for i in self.bot.colours.keys() if i not in ['edit']] + [i['tag'] for i in
                                                                                          self.bot.partners.values()] + [
            'empty']:
            colour = colour.lower()
        else:
            colour = None

        cllist = {}
        for k, v in self.bot.partners.items():
            cllist[v['tag']] = v['emoji']
        for k, v in self.bot.colours.items():
            cllist[k] = v
        cllist['empty'] = self.bot.empty.replace('<:', '').replace('>', '')

        header, display = self.screen_to_text(board, x, y, colour=colour, cllist=cllist)

        embed = discord.Embed(
            title=header, colour=self.blurplehex, timestamp=discord.utils.utcnow())

        embed.description = display

        embed.set_author(name=f"{board.name} | Use the arrows to choose the location and to confirm or cancel.")
        # embed.add_field(name = "Board", value = display)
        embed.set_footer(
            text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
            icon_url=self.bot.user.avatar)
        # msg = await ctx.reply(display, embed=embed)
        msg = await ctx.reply(embed=embed)

        if ctx.author.id not in self.bot.skipconfirm:
            # arrows = ["⬅", "⬆", "⬇", "➡", "blorpletick:436007034471710721", "blorplecross:436007034832551938"]
            # arrows2 = ["<:blorpletick:436007034471710721>", "<:blorplecross:436007034832551938>"]
            # for emote in arrows:
            #     await msg.add_reaction(emote)

            # def check(payload):
            #     return payload.user_id == ctx.author.id and payload.message_id == msg.id and (str(
            #         payload.emoji) in arrows or str(payload.emoji) in arrows2)

            while True:
                if False:  # just so i can collapse old commented-out code lol
                    pass
                    # done, pending = await asyncio.wait(
                    #     [
                    #         self.bot.wait_for(
                    #             'raw_reaction_add', timeout=30.0, check=check),
                    #         self.bot.wait_for(
                    #             'raw_reaction_remove', timeout=30.0, check=check)
                    #     ],
                    #     return_when=asyncio.FIRST_COMPLETED)

                    # try:
                    #     stuff = done.pop().result()
                    # except asyncio.TimeoutError:
                    #     embed.set_author(name="User timed out.")
                    #     await msg.edit(embed=embed)
                    #     try: await msg.clear_reactions()
                    #     except discord.Forbidden: pass
                    #     self.bot.cd.add(ctx.author.id)
                    #     try:
                    #         for future in done:
                    #             future.exception()
                    #         for future in pending:
                    #             future.cancel()
                    #     except asyncio.TimeoutError:
                    #         pass
                    #     return
                    # for future in done:
                    #     future.exception()
                    # for future in pending:
                    #     future.cancel()

                    # payload = stuff

                    # emojiname = str(payload.emoji)

                    # if emojiname == "<:blorplecross:436007034832551938>":
                    #     embed.set_author(name="Edit cancelled.")
                    #     await msg.edit(embed=embed)
                    #     await msg.clear_reactions()
                    #     self.bot.cd.add(ctx.author.id)
                    #     return
                    # elif emojiname == "<:blorpletick:436007034471710721>":
                    #     break

                    # if emojiname == "⬅" and x > 1: x -= 1
                    # elif emojiname == "➡" and x < board.width: x += 1
                    # elif emojiname == "⬇" and y < board.height: y += 1
                    # elif emojiname == "⬆" and y > 1: y -= 1

                view = NavigateView(ctx.author.id)
                await msg.edit(view=view)

                timeout = await view.wait()

                if timeout:
                    embed.set_author(name="User timed out.")
                    await msg.edit(embed=embed, view=None)
                    self.bot.cd.add(ctx.author.id)
                    return

                if view.confirm == True:
                    break
                elif view.confirm == False:
                    embed.set_author(name="Edit cancelled.")
                    await msg.edit(embed=embed, view=None)
                    self.bot.cd.add(ctx.author.id)
                    return

                if view.value == "L" and x > 1:
                    x -= 1
                elif view.value == "R" and x < board.width:
                    x += 1
                elif view.value == "D" and y < board.height:
                    y += 1
                elif view.value == "U" and y > 1:
                    y -= 1

                header, display = self.screen_to_text(board, x, y, colour=colour, cllist=cllist)

                embed.title = header
                embed.description = display
                # await msg.edit(content=display)
                await msg.edit(embed=embed)

            # await msg.clear_reactions()
            await msg.edit(view=None)

        if not colour:
            # embed.set_author(name="Use the reactions to choose a colour.")
            embed.set_author(name="Use the dropdown to choose a colour.")
            await msg.edit(embed=embed)

            colours = []
            # for i in self.bot.partners.values():
            #     if ctx.guild.id == int(i['guild']):
            #         colours.append(i['emoji'])
            for i in self.bot.partners.values():
                if ctx.guild.id == int(i['guild']):
                    colours.append(i)
            dcolours = [
                name for name, emoji in self.bot.colours.items()
                if name not in ['edit', 'blank']
            ]
            l = ['dred', 'brll', 'hpsq', 'yllw', 'gren', 'bhnt', 'blnc', 'ptnr', 'devl', 'blpl', 'dbpl', 'lpbl', 'ldbp',
                 'brvy', 'bstp', 'fchs', 'whte', 'ntgr', 'grpl', 'ntbl', 'dgry', 'nqbl']  # Order
            d = {n: i for n, i in zip(l, range(len(l)))}

            def sorter(i):
                # print(i, d[i])
                if i in d.keys():
                    return d[i]
                else:
                    return random.randint(100, 200)

            dcolours.sort(key=sorter)
            # ecolours = [self.bot.colours[i] for i in dcolours]
            ecolours = [[j for j in self.bot.coloursdict.values() if i == j['tag']][0] for i in dcolours]
            # print(ecolours)
            colours += ecolours
            # colours.append("blorplecross:436007034832551938")
            # for emoji in colours:
            #     # print(emoji)
            #     await msg.add_reaction(emoji)

            # def check(reaction, user):
            #     return user == ctx.author and reaction.message.id == msg.id and str(
            #         reaction.emoji).replace("<:", "").replace(">", "") in colours

            # try:
            #     reaction, user = await self.bot.wait_for(
            #         'reaction_add', timeout=30.0, check=check)
            # except asyncio.TimeoutError:
            #     embed.set_author(name="User timed out.")
            #     self.bot.cd.add(ctx.author.id)
            # else:
            #     if str(reaction.emoji) == "<:blorplecross:436007034832551938>":
            #         embed.set_author(name="Edit cancelled.")
            #         self.bot.cd.add(ctx.author.id)
            #     else:
            #         colour = reaction.emoji.name.replace("pl_", "")

            view = ColourView(ctx.author.id, colours)
            await msg.edit(view=view)

            timeout = await view.wait()

            if timeout:
                embed.set_author(name="User timed out.")
                await msg.edit(embed=embed, view=None)
                self.bot.cd.add(ctx.author.id)
                return

            if not view.confirm:
                embed.set_author(name="Edit cancelled.")
                await msg.edit(embed=embed, view=None)
                self.bot.cd.add(ctx.author.id)
                return

            colour = view.value

            if not colour:
                embed.set_author(name="No colour selected! - Edit cancelled.")
                await msg.edit(embed=embed, view=None)
                self.bot.cd.add(ctx.author.id)
                return

            await msg.edit(view=None)

        if colour:
            colours = []
            for i in self.bot.partners.values():
                if ctx.guild.id == int(i['guild']):
                    colours.append(i['tag'])
            colours += [
                name for name, emoji in self.bot.colours.items()
                if name not in ['edit']
            ]

            if colour not in colours and self.bot.partnercolourlock:
                return await ctx.reply(
                    f"That colour is not available within this server! To find out where you can use this colour, use `{ctx.prefix}colour {colour}`")

            olddata = copy.copy(board.data[str(y)][str(x)])

            # board.data[str(y)][str(x)] = {
            #     "c": colour,
            #     # "info": olddata['info'] + [{
            #     #     "user": ctx.author.id,
            #     #     "time": datetime.datetime.utcnow()
            #     # }]
            # }
            board.data[str(y)][str(x)] = colour
            async with self.bot.dblock:
                await self.update_history(board, colour, ctx.author.id, (x, y))
            embed.set_author(name="Pixel successfully set.")
            success = True

        header, display = self.screen_to_text(board, x, y, edit=False)

        # await msg.edit(content=display, embed=embed)
        embed.title = header
        embed.description = display
        await msg.edit(embed=embed)
        await msg.clear_reactions()

        if success:
            member = await ctx.bot.blurpleguild.fetch_member(ctx.author.id)
            if member and self.bot.artistrole not in [i.id for i in member.roles]:
                await member.add_roles(ctx.bot.blurpleguild.get_role(self.bot.artistrole))
                # t = ""
                # if ctx.author.guild.id != ctx.bot.blurpleguild.id: t = " in the Project Blurple server"
                # await ctx.reply(f"That was your first pixel placed! For that, you have received the **Artist** role{t}!")
                await ctx.reply(
                    f"That was your first pixel placed! For that, you have received the **Artist** role{' in the Project Blurple server' if ctx.author.guild.id != ctx.bot.blurpleguild.id else ''}!")

        async with self.bot.dblock:
            await self.bot.dbs.boards[board.name.lower()].bulk_write([
                UpdateOne({'row': y}, {'$set': {str(y): board.data[str(y)]}}),
                UpdateOne({'type': 'info'}, {'$set': {'info.last_updated': board.last_updated}})
            ])

        if success and ctx.author.id in self.bot.cooldownreminder:
            timeleft = cdexpiry - datetime.datetime.utcnow()
            if timeleft.days < 0:
                return await ctx.reply("Your cooldown has already expired! You can now place another pixel.")
            else:
                await asyncio.sleep(timeleft.seconds)
            await ctx.reply("Your cooldown has expired! You can now place another pixel.")

    def screen_to_text(self, board, x, y, *, zoom=11, edit=True, colour=None, cllist=None):
        loc, emoji, raw, zoom = self.screen(board, x, y, zoom)

        locx, locy = loc

        remoji = emoji[locy - 1][locx - 1]
        if edit:
            emoji[locy - 1][locx - 1] = "<:" + self.bot.colours["edit"] + ">"

        header = f"Blurple Canvas - ({x}, {y})"

        if locy - 2 >= 0: emoji[locy - 2].append(" ⬆")
        emoji[locy - 1].append(f" **{y}**")
        if locy < zoom: emoji[locy].append(" ⬇")

        emoji[0].append(f" {remoji}")
        emoji[1].append(f" <:now:1105112355219714168>")
        if colour:
            emoji[-2].append(f" <:new:1105112350371086346>")
            emoji[-1].append(f" <:{cllist[colour]}>")

        display = "\n".join(["".join(i) for i in emoji]) + "\n"

        if locx - 2 < 0:
            display += (str(self.bot.empty) * (locx - 2)) + f" **{x}** ➡"
        elif locx > zoom - 1:
            display += (str(self.bot.empty) * (locx - 2)) + f"⬅ **{x}**"
        else:
            display += (str(self.bot.empty) * (locx - 2)) + f"⬅ **{x}** ➡"

        return header, display

    @commands.command()
    @executive()
    async def paste(self, ctx, x: int, y: int, source=None):
        board = await self.findboard(ctx)
        if not board: return

        if board.locked == True:
            return await ctx.reply(f'This board is locked (view only)')

        empty = '----'

        if ctx.message.attachments:
            arraywh = await self.bot.loop.run_in_executor(None, self.pastefrombytes,
                                                          io.BytesIO(await ctx.message.attachments[0].read()))
            if isinstance(arraywh, str):
                return await ctx.reply(f"{arraywh}")
            else:
                array, width, height = arraywh

        elif source:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(source) as r:
                    raw = await r.text()

            rows = raw.split('\n')
            array = [i.split() for i in rows]

            width = len(sorted(array, key=len, reverse=True)[0])
            height = len(array)

            colours = [v['tag'] for v in self.bot.partners.values()] + [name for name, emoji in self.bot.colours.items()
                                                                        if name not in ['edit']] + [empty]

            if any([any([not v in colours for v in r]) for r in array]):
                return await ctx.reply(f"The source paste that you linked does not appear to be valid.")

        if board.width - x + 1 < width or board.height - y + 1 < height:
            return await ctx.reply(
                f"The paste does not appear to fit. Please make sure you are selecting the pixel position of the top-left corner of the paste.")

        for row, i in enumerate(array):
            for n, pixel in enumerate(i):
                if pixel == empty: continue
                board.data[str(y + row)][str(x + n)] = pixel
                async with self.bot.dblock:
                    await self.update_history(board, pixel, ctx.author.id, (x + n, y + row))

        await ctx.reply(f"Pasted!")

        async with self.bot.dblock:
            for row, i in enumerate(array):
                await self.bot.dbs.boards[board.name.lower()].update_one({'row': y + row}, {
                    '$set': {str(y + row): board.data[str(y + row)]}})

    def pastefrombytes(self, imgbytes):
        image = Image.open(imgbytes, 'r')
        # image = Image.open("canvaspastetest.png", "r")
        width, height = image.size
        pixel_values = list(image.getdata())

        channels = 4

        pixel_values = numpy.array(pixel_values).reshape((width, height, channels))

        colours = {**{v['rgb'][:3]: v['tag'] for v in self.bot.partners.values()},
                   **{v['rgb'][:3]: v['tag'] for v in self.bot.coloursdict.values() if
                      v['tag'] not in ['edit', 'blank']}}

        empty = '----'
        blank = 'blank'
        blankcode = (1, 1, 1)

        array = []
        for row, i in enumerate(pixel_values):
            array.append([])
            for n, pixel in enumerate(i):
                if len(pixel) == 4:
                    if pixel[3] == 0:
                        array[row].append(empty)
                        continue

                p = tuple(pixel[:3])

                if p == blankcode:
                    array[row].append(blank)
                    continue

                if p not in colours.keys(): return f"invalid pixel at ({n + 1}, {row + 1})"

                array[row].append(colours[p])

        return array, width, height

    @commands.command(aliases=['colors', 'colour', 'color', 'palette'])
    async def colours(self, ctx, palettes='all'):
        """Shows the full colour palette available. Type 'main' or 'partner' after the command to see a specific group of colours."""
        palettes = palettes.lower()
        if palettes in ['main', 'default']:
            palettes = 'main'
        elif palettes in ['partner', 'partners']:
            palettes = 'partner'
        else:
            cd = {k: v for k, v in self.bot.coloursdict.items() if k not in ['Edit tile', 'Blank tile']}
            cp = self.bot.partners
            colours = {v['tag']: v for k, v in {**cd, **cp}.items()}

            if palettes not in colours.keys():
                palettes = 'all'

        if palettes in ['main', 'partner', 'all']:
            image = discord.File(fp=copy.copy(self.bot.colourimg[palettes]),
                                 filename="Blurple_Canvas_Colour_Palette.png")

            embed = discord.Embed(
                title="Blurple Canvas Colour Palette", colour=self.blurplehex, timestamp=discord.utils.utcnow())
            embed.set_footer(
                text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                icon_url=self.bot.user.avatar)
            embed.set_image(url="attachment://Blurple_Canvas_Colour_Palette.png")
            await ctx.reply(embed=embed, file=image)

        else:
            c = colours[palettes]
            hexcode = '%02x%02x%02x' % c['rgb'][:-1]
            hexint = int(hexcode, 16)

            embed = discord.Embed(title=c['name'], colour=hexint)
            embed.set_footer(
                text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                icon_url=self.bot.user.avatar)
            embed.add_field(name=f"RGB{c['rgb'][:-1]}", value=f"<:{c['emoji']}> - #{hexcode.upper()}", inline=False)
            if c['guild']:
                if self.bot.partnercolourlock:
                    g = self.bot.get_guild(int(c['guild']))
                    if g:
                        server = f"This colour is only available in the **{g.name}** ({g.id}) server!"
                    else:
                        server = f"This colour is only available in {c['guild']}... that I can't seem to see? Please let Rocked03#3304 know!!"
                else:
                    server = f"This is a partnered server colour, however it's been set to be able to be used anywhere!"
            else:
                server = f"This is a default colour, it's available to use everywhere!"
            embed.add_field(name=f"Usability", value=server)
            await ctx.reply(embed=embed)

    # @app_commands.guilds(559341262302347314)

    @app_commands.command(name="palette")
    async def slash_palette(self, interaction: discord.Interaction,
                            palette: typing.Literal['default', 'partner', 'all'] = "all") -> None:
        """Shows the available colour palette"""
        palette = palette.lower()
        if palette == "default": palette = "main"

        image = discord.File(fp=copy.copy(self.bot.colourimg[palette]), filename="Blurple_Canvas_Colour_Palette.png")

        embed = discord.Embed(
            title="Blurple Canvas Colour Palette", colour=self.blurplehex, timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"{palette.capitalize()} colours", icon_url=self.bot.user.avatar)
        embed.set_image(url="attachment://Blurple_Canvas_Colour_Palette.png")
        await interaction.response.send_message(embed=embed, file=image)

    # @slash_palette.autocomplete('palette')
    # async def slash_palette_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    #     palettes = ["default", "partner", "all"]
    #     return [app_commands.Choice(name=i, value=i) for i in palettes if current.lower() in i.lower()]

    @commands.command(aliases=['reloadcolors'])
    @admin()
    async def reloadcolours(self, ctx):
        self.bot.colourimg = {
            x: await self.bot.loop.run_in_executor(None, self.image.colours, self, x) for x in
            ['main', 'partner', 'all']
        }
        await ctx.reply("Done")

    @commands.command(aliases=['tpcel'])
    @executive()
    async def togglepartnercolourexclusivitylock(self, ctx):
        self.bot.partnercolourlock = not self.bot.partnercolourlock
        await ctx.reply(f"Set the partner colour exclusivity lock to {self.bot.partnercolourlock}")

    @commands.command()
    @dev()
    async def debugraw(self, ctx):
        board = await self.findboard(ctx)
        if not board: return

        print(board.data)
        # print([[xv["c"] for xv in xk.values()]
        #        for xk in board.data.values()])
        print([list(xk.values()) for xk in board.data.values()])
        await ctx.message.add_reaction("👍")

    @commands.command(hidden=True)
    async def test(self, ctx):
        print([guild.name for guild in self.bot.guilds])

    @commands.command(name="viewnh", aliases=["seenh"])
    @commands.cooldown(1, 30, BucketType.user)
    @inteam()
    async def viewnh(self, ctx, *, xyz: coordinates = None):
        """Views a section of the board as an image. Must have xy coordinates, zoom (no. of tiles wide) optional."""
        board = await self.findboard(ctx)
        if not board: return

        if not xyz: return await ctx.reply(f'Please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom = xyz

        if board.data == None:
            return await ctx.reply('There is currently no board created')

        if x < 1 or x > board.width or y < 1 or y > board.height:
            return await ctx.reply(
                f'Please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )

        defaultzoom = 25

        if zoom == None or zoom > board.width or zoom > board.height:
            zoom = defaultzoom
        if zoom > board.width or zoom > board.height:
            if board.width > board.height:
                zoom = board.width
            else:
                zoom = board.height
        if zoom < 5:
            return await ctx.reply(f'Please have a minumum zoom of 5 tiles')

        async with aiohttp.ClientSession() as session:
            async with ctx.typing():
                start = time.time()
                image = await self.bot.loop.run_in_executor(
                    None, self.image.imager, self, board, x, y, zoom, False)
                end = time.time()
                image = discord.File(fp=image, filename=f'board_{x}-{y}.png')

                embed = discord.Embed(
                    colour=self.blurplehex, timestamp=discord.utils.utcnow())
                embed.set_author(name=f"{board.name} | Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                await ctx.reply(embed=embed, file=image)


class NavigateView(discord.ui.View):
    def __init__(self, userid: int):
        super().__init__(timeout=30.0)
        self.value = None
        self.confirm = None
        self.userid = userid

    @discord.ui.button(emoji="<:blorpletick:436007034471710721>", style=discord.ButtonStyle.green, row=0,
                       custom_id="confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirm = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(emoji="⬆️", style=discord.ButtonStyle.grey, row=0)
    async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "U"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(emoji="<:blorplecross:436007034832551938>", style=discord.ButtonStyle.red, row=0,
                       custom_id="cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirm = False
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.grey, row=1)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "L"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(emoji="⬇️", style=discord.ButtonStyle.grey, row=1)
    async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "D"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.grey, row=1)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "R"
        await interaction.response.defer()
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.userid


class ColourSelect(discord.ui.Select):
    def __init__(self, colours: list):
        options = []

        for i in colours:
            options.append(discord.SelectOption(label=i['name'], value=i['tag'], emoji=i['emoji']))

        super().__init__(placeholder="Select which colour to place...", min_values=1, max_values=1, options=options)

        self.selected = None
        self.row = 0

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


class ColourView(discord.ui.View):
    def __init__(self, userid: int, colours: list):
        super().__init__(timeout=30.0)

        self.dropdown = ColourSelect(colours)
        self.add_item(self.dropdown)

        self.confirm = False
        self.value = None
        self.userid = userid

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.userid

    @discord.ui.button(emoji="<:blorpletick:436007034471710721>", style=discord.ButtonStyle.green, row=1,
                       custom_id="confirm")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirm = True
        if self.dropdown.values: self.value = self.dropdown.values[0]
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(emoji="<:blorplecross:436007034832551938>", style=discord.ButtonStyle.red, row=1,
                       custom_id="cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.stop()


async def setup(bot):
    await bot.add_cog(CanvasCog(bot))
