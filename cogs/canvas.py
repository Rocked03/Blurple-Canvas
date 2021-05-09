import aiohttp, asyncio, colorsys, copy, datetime, discord, io, json, math, motor.motor_asyncio, numpy, PIL, pymongo, random, sys, textwrap, time, traceback, typing
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from PIL import Image, ImageDraw, ImageFont
from pymongo import UpdateOne
# pillow, motor, pymongo, discord.py, numpy


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
    async def pred(ctx): return any(elem in [v for k, v in ctx.bot.modroles.items()] for elem in [i.id for i in (await ctx.bot.blurpleguild.fetch_member(ctx.author.id)).roles])
    return commands.check(pred)

def executive():
    async def pred(ctx): return any(i in [ctx.bot.modroles['Admin'], ctx.bot.modroles['Executive'], ctx.bot.modroles['Exec Assist']] for i in [i.id for i in (await ctx.bot.blurpleguild.fetch_member(ctx.author.id)).roles])
    return commands.check(pred)

def admin():
    # async def pred(ctx): return any(elem in [v for k, v in ctx.bot.modroles.items() if k == "Admin"] for elem in [i.id for i in ctx.bot.blurpleguild.fetch_member(ctx.author.id).roles])
    async def pred(ctx): return ctx.bot.modroles['Admin'] in [i.id for i in (await ctx.bot.blurpleguild.fetch_member(ctx.author.id)).roles]
    return commands.check(pred)



# todo
# a la blob emoji, cooldown expiry ping
# persistent ts, board
# reload bot without breaking stuff






class CanvasCog(commands.Cog, name="Canvas"):
    """Canvas Module"""

    def __init__(self, bot):
        self.bot = bot

        self.bot.initfinished = False

        self.bot.modroles = {
            "Admin":       443013283977494539,
            "Executive":   413213839866462220,
            "Exec Assist": 470272155876065280,
            "Moderator":   569015549225598976,
            "Helper":      442785212502507551,
        }

        self.bot.cd = set()

        # self.bot.teams = {
        #     "light": 573011450231259157,
        #     "dark": 573011441683005440,
        # }
        self.bot.teams = {"blurple user": 705295796773584976}

        self.bot.artistrole = 799240276542619649

        self.bot.skipconfirm = []

        self.bot.uboards = {}

        self.bot.boards = dict()

        self.bot.partnercolourlock = True

        self.bot.defaultcanvas = "Canvas"
        self.bot.ignoredcanvases = ['mini', 'main2019', 'main2020', 'staff', 'example', 'big', 'canvasold']


        self.bot.pymongo = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://Rocked03:eem8yFOpEnm5dW1Y@blurple-canvas.lj40x.mongodb.net/test?retryWrites=true&w=majority")
        self.bot.pymongoog = pymongo.MongoClient("mongodb+srv://Rocked03:eem8yFOpEnm5dW1Y@blurple-canvas.lj40x.mongodb.net/test?retryWrites=true&w=majority")

        async def getboards(self):
            print('Loading boards off DB')

            class dbs():
                def __init__(self, bot):
                    self.users = bot.pymongo.users
                    self.boards = bot.pymongo.boards

            self.bot.dbs = dbs(self.bot)

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
                    boarddata = list(board.find({}))
                    info = next(x for x in boarddata if x['type'] == 'info')['info']
                    history = next(x for x in boarddata if x['type'] == 'history')['history']
                    print(info)
                    data = [x for x in boarddata if x['type'] == 'data']
                    print(f"Saving data...")
                    d = {k: v for d in data for k, v in d.items()}
                    self.bot.boards[info['name'].lower()] = self.board(name = info['name'], width = info['width'], height = info['height'], locked = info['locked'], data = d, history = history)

                    print(f"Loaded '{name}'")

                print('All boards loaded')

            some_stuff = await bot.loop.run_in_executor(None, loadboards, self)

            for b in self.bot.boards.keys():
                self.bot.loop.create_task(self.backup(b))

        self.bot.loop.create_task(getboards(self))

        async def reloadpymongo(self):
            while True:
                await asyncio.sleep(1800) # 30 minutes
                self.bot.pymongo = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://Rocked03:eem8yFOpEnm5dW1Y@blurple-canvas.lj40x.mongodb.net/test?retryWrites=true&w=majority")
                self.bot.pymongoog = pymongo.MongoClient("mongodb+srv://Rocked03:eem8yFOpEnm5dW1Y@blurple-canvas.lj40x.mongodb.net/test?retryWrites=true&w=majority")
        self.bot.loop.create_task(reloadpymongo(self))


        async def loadcolourimg(self):
            self.bot.colourimg = {
                x: await self.bot.loop.run_in_executor(None, self.image.colours, self, x) for x in ['all', 'main', 'partner']
            }
        self.bot.loop.create_task(loadcolourimg(self))


        async def fetchserver(self):
            self.bot.blurpleguild = await self.bot.fetch_guild(412754940885467146)
            await asyncio.sleep(60)
        self.bot.loop.create_task(fetchserver(self))



        self.bot.initfinished = True


    class board():
        def __init__(self, *, name, width, height, locked, data = dict(), history = dict()):
            self.data = data
            self.name = name
            self.width = width
            self.height = height
            self.locked = locked
            self.history = history

    class image():
        font = lambda x: ImageFont.truetype("Uni Sans Heavy.otf", x)
        fontxy =  font(60)
        fonttitle = font(18)
        fontcoordinates = font(21)
        fontcolourtitle = font(120)

        def imager(self, aboard, x, y, zoom, highlight = True):
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
                imagemax = 2000
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

            board = Image.new('RGBA', size, (114, 137, 218, 255))
            draw = ImageDraw.Draw(board)
            draw.rectangle([(borderwidth + 1, borderwidth + 1), size],
                           fill=(78, 93, 148, 255))

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
                    fill=(78, 93, 148, 255),
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
                    fill=(78, 93, 148, 255),
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
                'main': 4,
                'partner': 6
            }[palettes]

            namefont = self.image.font(int(round(squaresize / 6.5, 0)))
            codefont = self.image.font(int(round(squaresize / 9, 0)))

            basecorners = 50
            squarecorners = 50

            namewidth = 10


            def hsl(x):
                if len(x) > 3: x = x[:3]
                to_float = lambda x : x / 255.0
                (r, g, b) = map(to_float, x)
                h, s, l = colorsys.rgb_to_hsv(r,g,b)
                h = h if 0 < h else 1 # 0 -> 1
                return h, s, l
            rainbow = lambda x: {k: v for k, v in sorted(x.items(), key = lambda kv: hsl(kv[1]['rgb']))}

            shuffle = lambda x: {k: v for k, v in sorted(x.items(), key = lambda kv: random.randint(1, 99999999))}

            allcolours = {}
            
            if palettes in ['all', 'main']:
                allcolours['Main Colours'] = rainbow({k: v for k, v in self.bot.coloursdict.items() if k not in ['Edit tile', 'Blank tile']})
            if palettes in ['all', 'partner']:
                allcolours['Partner Colours'] = rainbow(self.bot.partners)


            height = 2 * borderwidth
            for i in allcolours.values():
                height += textspacing
                height += squaresize * math.ceil(len(i) / squaren)
            height += borderwidth * (len(allcolours) - 1)
            
            width = 2 * borderwidth + squaren * squaresize

            # img = Image.new('RGBA', (width, height), (114, 137, 218, 127))
            img = self.image.round_rectangle(self, (width, height), basecorners, (114, 137, 218, 75), allcorners = True)
            draw = ImageDraw.Draw(img)

            space = 0
            for name, cs in allcolours.items():
                bg = self.image.round_rectangle(self,
                        (squaren * squaresize, textspacing + squaresize * math.ceil(len(cs) / squaren)),
                        squarecorners, (78, 93, 148, 255), allcorners = True
                    )
                img.paste(bg, (borderwidth, borderwidth + space), bg)

                tsx, tsy = draw.textsize(name, font=self.image.fontcolourtitle)

                draw.text((int(round(((width - tsx) / 2), 0)),
                       int(round(((textspacing - tsy) / 2 + space + borderwidth), 0))),
                      name,
                      font=self.image.fontcolourtitle,
                      fill=(255, 255, 255, 255))

                rows = [[] for i in range(math.ceil(len(i) / squaren))]
                for n, (k, c) in enumerate(cs.items()):
                    rows[math.floor(n / squaren)].append(c)
                if not rows[-1]: rows.pop(len(rows) - 1)

                def roundrect(img, colour, coords, corners):
                    a = self.image.round_rectangle(
                        self, (squaresize, squaresize), squarecorners, colour,
                        topleft=corners['tl'], topright=corners['tr'], bottomleft=corners['bl'], bottomright=corners['br']
                    )
                    img.paste(a, coords, a)
                    return img

                for rown, row in enumerate(rows):
                    for pos, cdict in enumerate(row):
                        xpos = borderwidth + pos * squaresize #+ (squaren - len(row)) * squaresize / 2
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
                                fill = cdict['rgb']
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
                            font = namefont,
                            fill = tcolour,
                            align = 'center',
                            spacing = int(round(squaresize / 30))


                        )

                        rgbtxt = ', '.join([str(i) for i in cdict['rgb'][:3]])
                        tsnx, tsny = draw.textsize(rgbtxt, font=codefont)
                        draw.text(
                            (
                                int(round(xpos + (squaresize - tsnx) / 2, 0)),
                                int(round(ypos + squaresize / 10, 0))
                            ),
                            rgbtxt,
                            font = codefont,
                            fill = tcolour,
                        )

                        tsnx, tsny = draw.textsize(cdict['tag'], font=codefont)
                        draw.text(
                            (
                                int(round(xpos + (squaresize - tsnx) / 2, 0)),
                                int(round(ypos + (squaresize - tsny) - squaresize / 10, 0))
                            ),
                            cdict['tag'],
                            font = codefont,
                            fill = tcolour,
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

        def round_rectangle(self, size, radius, fill, topleft=False, topright=False, bottomleft=False, bottomright=False, allcorners=False):
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

                if len(arg) < 3: zoom = None
                else:
                    if self.colour and len(arg) == 3: zoom = None
                    else: zoom = int(arg[2])

                if self.colour: colour = arg[-1]

                x = int(arg[0].replace('(', '').replace(',', ''))
                y = int(arg[1].replace(')', ''))
            except Exception as e:
                x, y, zoom, colour = (0, 0, None, None)

            if self.colour: return (x, y, zoom, colour)
            else: return (x, y, zoom)

    
    async def cog_check(self, ctx):
        return ctx.guild.id in [self.bot.blurpleguild.id] + [int(i) for i in self.bot.partners.keys()]

    @commands.Cog.listener()  # Error Handler
    async def on_command_error(self, ctx, error):
        ignored = (commands.CommandNotFound, commands.UserInputError, asyncio.TimeoutError, asyncio.exceptions.TimeoutError, commands.CommandInvokeError)
        if isinstance(error, ignored): return

        if isinstance(error, commands.CheckFailure):
            # print(error)
            # await ctx.send(f"{ctx.author.mention}, It doesn't look like you are allowed to run this command. Make sure you've got the Blurple User role in the main server, otherwise these commands will not work!")
            await ctx.send(f"{ctx.author.mention}, It doesn't look like you are allowed to run this command. Make sure you're in the host Project Blurple server, otherwise these commands will not work!")
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
                await ctx.send(
                    f"{ctx.author.mention}, this command is on cooldown ({minutes}m, {seconds}s)"
                )
            else:
                await ctx.send(
                    f"{ctx.author.mention}, this command is on cooldown ({seconds}s)"
                )
            return

        if isinstance(error, discord.Forbidden):
            await ctx.send(
                f"{ctx.author.mention}, I don't seem to have the right permissions to do that. Please check with the mods of this server that I have Embed Links // Send Images // Manage Message (for clearing reactions) perms!"
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

    async def history(self, board, colour, author, coords):
        time = str(datetime.datetime.utcnow().timestamp()).replace('.', '_')
        try:
            board.history[time].append([coords, colour, author])
        except KeyError:
            # await asyncio.sleep(random.randint(1, 10) / 100)
            # try:
            #     board.history[time].append([coords, colour, author])
            # except KeyError:
            board.history[time] = [[coords, colour, author]]


    async def backup(self, boardname):
        n = 1
        nbackups = 4
        period = 300 # seconds // 5 minutes
        while True:
            await asyncio.sleep(period)
            try:
                print(f"Starting backup of {boardname}_{n}")
                async with aiohttp.ClientSession() as session:
                    with open(f'backups/backup_{boardname}_{n}.json', 'wt') as f:
                        data = {i: getattr(self.bot.boards[boardname], i) for i in ['data', 'name', 'width', 'height', 'locked', 'history']}
                        try: data['data'].pop('_id')
                        except KeyError: pass
                        json.dump(data, f)

                print(f"Saved backup {boardname}_{n}   {datetime.datetime.utcnow()}")
                n = n + 1 if n < nbackups else 1
            except Exception as e: print(e)

    @commands.command()
    @admin()
    async def loadbackup(self, ctx, n:int, boardname):
        async with aiohttp.ClientSession() as session:
            with open(f'backups/backup_{boardname}_{n}.json', 'rt') as f:
                data = json.load(f)
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
                    colour=0x7289da, timestamp=datetime.datetime.utcnow())
                embed.set_author(name=f"{board.name} | Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar_url)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                await ctx.send(embed=embed, file=image)

        await ctx.send("Is this what you're looking for?")

        def check(message):
            return ctx.author == message.author and message.content.lower() in ['yes', 'no', 'y', 'n'] and message.channel == ctx.message.channel

        msg = await self.bot.wait_for('message', check=check)
        
        if msg.content in ['no', 'n']:
            return await ctx.send("Ok, cancelled")

        await ctx.send("Ok, pushing to db - please make sure the board exists so I can update it")


        t1 = time.time()

        newboard = board

        self.bot.boards[boardname] = newboard

        await ctx.send('Writing to db')
        print('Writing to db')

        dboard = self.bot.dbs.boards.get_collection(newboard.name.lower())
        await dboard.bulk_write([
            UpdateOne({'type': 'info'}, {'$set': {'info': {'name': newboard.name, 'width': newboard.width, 'height': newboard.height, 'locked': False}}}),
            UpdateOne({'type': 'history'}, {'$set': {'history': newboard.history}}),
        ])

        print('Info done')
        await ctx.send('Info done')

        await self.bot.dbs.boards[board.name.lower()].bulk_write([UpdateOne({'row': y+1}, {'$set': {str(y+1): newboard.data[str(y+1)]}}) for y in range(newboard.height)])

        t2 = time.time()

        print('Board saved')
        await ctx.send(f"Board saved ({round((t2 - t1), 4)}s)")



    @commands.command(name="createboard", aliases=["cb"])
    @admin()
    async def createboard(self, ctx, x: int, y: int, seed: typing.Optional[boardspec] = None, *, name: str):
        """Creates a board. Optional seed parameter. Must specify width (x), height (y), and name."""
        if not self.bot.initfinished: return await ctx.send('Please wait for the bot to finish retrieving boards from database.')

        if any(i < 5 for i in [x, y]):
            return await ctx.send("Please have a minimum of 5.")

        await ctx.send("Creating board...")

        fill = "blank"

        try:
            self.bot.boards[name.lower()]
        except Exception:
            pass
        else:
            return await ctx.send("There's already a board with that name!")

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
                await self.history(newboard, colour, "Automatic", (xn, yn))

        await ctx.send("Created board, saving to database")

        await self.bot.dbs.boards.create_collection(newboard.name.lower())
        dboard = self.bot.dbs.boards.get_collection(newboard.name.lower())
        await dboard.insert_many([
            {'type': 'info', 'info': {'name': newboard.name, 'width': newboard.width, 'height': newboard.height, 'locked': False}},
            {'type': 'history', 'history': newboard.history},
        ])

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
                try: ndata.append({str(cline): newboard.data[str(cline)], 'type': 'data', 'row': cline})
                except KeyError: pass
                cline += 1
            datalist.append(ndata)

            n -= lines * newboard.width

        # print(n / newboard.width)
        ndata = []
        for i in range(n):
            try: ndata.append({str(cline): newboard.data[str(cline)], 'type': 'data', 'row': cline})
            except KeyError: pass
            cline += 1
        datalist.append(ndata)

        for x, item in enumerate(datalist): 
            await dboard.insert_many(item)
            await ctx.send(f'Saved chunk {x + 1} of {len(datalist)}')

        t2 = time.time()

        await ctx.send(f"Board created ({round((t2 - t1), 4)}s)")

    @commands.command()
    @inteam()
    async def boards(self, ctx):
        """Lists all available canvas boards"""
        await ctx.send(f'Boards ({len(self.bot.boards)}) - ' + ' | '.join(self.bot.boards.keys()))

    @commands.command()
    @inteam()
    async def join(self, ctx, *, name: str = None):
        """Joins a board. You need to have joined a board to start interacting with the canvas."""
        if not name: return await ctx.send(f'{ctx.author.mention}, please specify a board to join. To see all valid boards, type `{ctx.prefix}boards`.')

        if name.lower() not in self.bot.boards.keys():
            return await ctx.send(
                f'{ctx.author.mention}, that is not a valid board. To see all valid boards, type `{ctx.prefix}boards`.'
            )

        self.bot.uboards[ctx.author.id] = name.lower()

        bname = self.bot.boards[name.lower()].name
        await ctx.send(f"Joined '{bname}' board")

    async def findboard(self, ctx):
        try:
            self.bot.boards[self.bot.uboards[ctx.author.id]]
        except KeyError:
            if self.bot.defaultcanvas.lower() in [i.lower() for i in self.bot.boards.keys()]:
                self.bot.uboards[ctx.author.id] = self.bot.defaultcanvas.lower()
                await ctx.send(f"{ctx.author.mention}, you weren't added to a board, so I've automatically added you to the default '{self.bot.defaultcanvas}' board. To see all available boards, type `{ctx.prefix}boards`")
            else:
                await ctx.send(
                    f"{ctx.author.mention}, You haven't joined a board! Type `{ctx.prefix}join <board>` to join a board! To see all boards, type `{ctx.prefix}boards`"
                )
                return False

        return self.bot.boards[self.bot.uboards[ctx.author.id]]

    @commands.command(name="toggleskip", aliases=["ts"])
    @inteam()
    async def toggleskip(self, ctx):
        """Toggles p/place coordinate confirmation"""
        if ctx.author.id in self.bot.skipconfirm:
            self.bot.skipconfirm.remove(ctx.author.id)
            await ctx.send(f'Re-enabled confirmation message for {ctx.author.mention}')
        else:
            self.bot.skipconfirm.append(ctx.author.id)
            await ctx.send(f"Disabled confirmation message for {ctx.author.mention}")

    @commands.command(name="view", aliases=["see"])
    @commands.cooldown(1, 10, BucketType.user)
    @inteam()
    async def view(self, ctx, *, xyz: coordinates = None):
        """Views a section of the board as an image. Must have xy coordinates, zoom (no. of tiles wide) optional."""
        board = await self.findboard(ctx)
        if not board: return

        # if not xyz: return await ctx.send(f'{ctx.author.mention}, please specify coordinates (e.g. `234 837` or `12 53`)')

        if xyz:
            x, y, zoom = xyz

            if board.data == None:
                return await ctx.send('{ctx.author.mention}, there is currently no board created')

            if x < 1 or x > board.width or y < 1 or y > board.height:
                return await ctx.send(
                    f'{ctx.author.mention}, please send coordinates between (1, 1) and ({board.width}, {board.height})'
                )

            defaultzoom = 25

            if zoom == None or zoom > board.width or zoom > board.height:
                zoom = defaultzoom
            if zoom > board.width or zoom > board.height:
                if board.width > board.height: zoom = board.width
                else: zoom = board.height
            if zoom < 5:
                return await ctx.send(f'{ctx.author.mention}, please have a minumum zoom of 5 tiles')
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
                    colour=0x7289da, timestamp=datetime.datetime.utcnow())
                embed.set_author(name=f"{board.name} | Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar_url)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                await ctx.send(embed=embed, file=image)

    @commands.command(name="viewnav", aliases=["seenav"])
    @commands.cooldown(1, 30, BucketType.user)
    @inteam()
    async def viewnav(self, ctx, *, xyz: coordinates = None):
        """Views a section of the boards as an inline image created with emojis. Can be navigatable via interactive input. Must have xy coordinates."""
        board = await self.findboard(ctx)
        if not board: return

        if not xyz: return await ctx.send(f'{ctx.author.mention}, please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom = xyz

        if board.data == None:
            return await ctx.send('{ctx.author.mention}, there is currently no board created')

        if x < 1 or x > board.width or y < 1 or y > board.height:
            return await ctx.send(
                f'{ctx.author.mention}, please send coordinates between (1, 1) and ({board.width}, {board.height})'
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
            colour=0x7289da, timestamp=datetime.datetime.utcnow())
        # embed.add_field(name = "Board", value = display)
        embed.set_footer(
            text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
            icon_url=self.bot.user.avatar_url)
        embed.set_author(name=board.name)
        msg = await ctx.send(display, embed=embed)

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
                for future in done:
                    future.exception()
                for future in pending:
                    future.cancel()
                return
            for future in done:
                future.exception()
            for future in pending:
                future.cancel()

            payload = stuff

            emojiname = str(payload.emoji)
            if emojiname == "⬅" and x > 1: x -= 1
            elif emojiname == "➡" and x < board.width: x += 1
            elif emojiname == "⬇" and y < board.height: y += 1
            elif emojiname == "⬆" and y > 1: y -= 1

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

    @commands.command(hidden=True)
    @dev()
    async def viewnavexp(self, ctx, *, xyz: coordinates = None):
        board = await self.findboard(ctx)
        if not board: return

        if not xyz: return await ctx.send('{ctx.author.mention}, please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom = xyz

        if x < 1 or x > board.width or y < 1 or y > board.height:
            return await ctx.send(
                f'{ctx.author.mention}, please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )

        if zoom == None:
            if board.width > board.height: zoom = board.width
            else: zoom = board.height
        if zoom > board.width or zoom > board.height:
            if board.width > board.height: zoom = board.width
            else: zoom = board.height
        if zoom < 5:
            return await ctx.send(f'{ctx.author.mention}, please have a minumum zoom of 5 tiles')

        async with aiohttp.ClientSession() as session:
            async with ctx.typing():
                start = time.time()
                image = await self.bot.loop.run_in_executor(
                    None, self.image.imager, self, board, x, y, zoom)
                end = time.time()
                image = discord.File(fp=image, filename=f'board_{x}-{y}.png')

                embed = discord.Embed(
                    colour=0x7289da, timestamp=datetime.datetime.utcnow())
                embed.set_author(name=f"Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar_url)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                msg = await ctx.send(embed=embed, file=image)

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
            if emojiname == "⬅" and x > 1: x -= 1
            elif emojiname == "➡" and x < board.width: x += 1
            elif emojiname == "⬇" and y < board.height: y += 1
            elif emojiname == "⬆" and y > 1: y -= 1

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

    @commands.command()
    @inteam()
    @commands.cooldown(1, 30, BucketType.user)  # 1 msg per 30s
    async def place(self, ctx, *, xyz: coordinates(True) = None):
        """Places a tile at specified location. Must have xy coordinates. Same inline output as viewnav. Choice to reposition edited tile before selecting colour. Cooldown of 5 minutes per tile placed."""
        board = await self.findboard(ctx)
        if not board: return

        if board.locked == True:
            return await ctx.send(f'{ctx.author.mention}, this board is locked (view only)')
        
        if ctx.author in self.bot.cd: self.bot.cd.remove(ctx.author.id)

        if not board: 
            self.bot.cd.add(ctx.author.id)
            return

        if not xyz: 
            self.bot.cd.add(ctx.author.id)
            return await ctx.send(f'{ctx.author.mention}, please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom, colour = xyz

        if board.data == None:
            await ctx.send('{ctx.author.mention}, there is currently no board created')
            self.bot.cd.add(ctx.author.id)
            return

        if x < 1 or x > board.width or y < 1 or y > board.height:
            self.bot.cd.add(ctx.author.id)
            await ctx.send(
                f'{ctx.author.mention}, please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )
            return

        success = False

        if colour.lower() == 'blnk': colour = 'blank'
        if colour.lower() in [i for i in self.bot.colours.keys() if i not in ['edit']] + [i['tag'] for i in self.bot.partners.values()] + ['empty']:
            colour = colour.lower()
        else: colour = None

        cllist = {}
        for k, v in self.bot.partners.items():
            cllist[v['tag']] = v['emoji']
        for k, v in self.bot.colours.items():
            cllist[k] = v
        cllist['empty'] = self.bot.empty.replace('<:','').replace('>','')

        loc, emoji, raw, zoom = self.screen(board, x, y)
        locx, locy = loc
        remoji = emoji[locy - 1][locx - 1]
        emoji[locy - 1][locx - 1] = "<:" + self.bot.colours["edit"] + ">"

        display = f"**Blurple Canvas - ({x}, {y})**\n"

        if locy - 2 >= 0: emoji[locy - 2].append(" ⬆")
        emoji[locy - 1].append(f" **{y}** (y)")
        if locy < zoom: emoji[locy].append(" ⬇")

        emoji[0].append(f" | {remoji} (Current pixel)")
        if colour: emoji[-1].append(f" | <:{cllist[colour]}> (Selected colour)")

        display += "\n".join(["".join(i) for i in emoji]) + "\n"

        if locx - 2 < 0:
            display += (self.bot.empty * (locx - 2)) + f" **{x}** (x) ➡"
        elif locx > zoom - 1:
            display += (self.bot.empty * (locx - 2)) + f"⬅ **{x}** (x)"
        else:
            display += (self.bot.empty * (locx - 2)) + f"⬅ **{x}** (x) ➡"

        # display = "\n".join(["".join(i) for i in emoji])
        embed = discord.Embed(
            colour=0x7289da, timestamp=datetime.datetime.utcnow())
        embed.set_author(name = f"{board.name} | Use the arrow reactions to choose the location and to confirm or cancel.")
        # embed.add_field(name = "Board", value = display)
        embed.set_footer(
            text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
            icon_url=self.bot.user.avatar_url)
        msg = await ctx.send(display, embed=embed)

        if ctx.author.id not in self.bot.skipconfirm:
            arrows = ["⬅", "⬆", "⬇", "➡", "blorpletick:436007034471710721", "blorplecross:436007034832551938"]
            arrows2 = ["<:blorpletick:436007034471710721>", "<:blorplecross:436007034832551938>"]
            for emote in arrows:
                await msg.add_reaction(emote)

            def check(payload):
                return payload.user_id == ctx.author.id and payload.message_id == msg.id and (str(
                    payload.emoji) in arrows or str(payload.emoji) in arrows2)


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
                    embed.set_author(name="User timed out.")
                    await msg.edit(embed=embed)
                    try: await msg.clear_reactions()
                    except discord.Forbidden: pass
                    self.bot.cd.add(ctx.author.id)
                    try:
                        for future in done:
                            future.exception()
                        for future in pending:
                            future.cancel()
                    except asyncio.TimeoutError:
                        pass
                    return
                for future in done:
                    future.exception()
                for future in pending:
                    future.cancel()

                payload = stuff

                emojiname = str(payload.emoji)

                if emojiname == "<:blorplecross:436007034832551938>":
                    embed.set_author(name="Edit cancelled.")
                    await msg.edit(embed=embed)
                    await msg.clear_reactions()
                    self.bot.cd.add(ctx.author.id)
                    return
                elif emojiname == "<:blorpletick:436007034471710721>":
                    break

                if emojiname == "⬅" and x > 1: x -= 1
                elif emojiname == "➡" and x < board.width: x += 1
                elif emojiname == "⬇" and y < board.height: y += 1
                elif emojiname == "⬆" and y > 1: y -= 1

                loc, emoji, raw, zoom = self.screen(board, x, y)

                locx, locy = loc

                remoji = emoji[locy - 1][locx - 1]
                emoji[locy - 1][locx - 1] = "<:" + self.bot.colours["edit"] + ">"

                display = f"**Blurple Canvas - ({x}, {y})**\n"

                if locy - 2 >= 0: emoji[locy - 2].append(" ⬆")
                emoji[locy - 1].append(f" **{y}** (y)")
                if locy < zoom: emoji[locy].append(" ⬇")

                emoji[0].append(f" | {remoji} (Current pixel)")
                if colour: emoji[-1].append(f" | <:{cllist[colour]}> (Selected colour)")

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

            await msg.clear_reactions()

        if not colour:
            embed.set_author(name="Use the reactions to choose a colour.")
            await msg.edit(embed=embed)

            colours = []
            if str(ctx.guild.id) in self.bot.partners.keys():
                colours.append(self.bot.partners[str(ctx.guild.id)]['emoji'])
            dcolours = [
                name for name, emoji in self.bot.colours.items()
                if name not in ['edit', 'blank']
            ]
            l = ['brll', 'hpsq', 'bhnt', 'blnc', 'ptnr', 'devl', 'blpl', 'dbpl', 'brvy', 'bstp', 'whte', 'ntgr', 'grpl', 'ntbl', 'dgry', 'nqbl'] # Order
            d = {n: i for n, i in zip(l, range(len(l)))}
            def sorter(i): 
                # print(i, d[i])
                if i in d.keys():
                    return d[i]
                else: return random.randint(100, 200)
            dcolours.sort(key=sorter)
            ecolours = [self.bot.colours[i] for i in dcolours]
            # print(ecolours)
            colours += ecolours
            colours.append("blorplecross:436007034832551938")
            for emoji in colours:
                # print(emoji)
                await msg.add_reaction(emoji)

            def check(reaction, user):
                return user == ctx.author and reaction.message.id == msg.id and str(
                    reaction.emoji).replace("<:", "").replace(">", "") in colours

            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add', timeout=30.0, check=check)
            except asyncio.TimeoutError:
                embed.set_author(name="User timed out.")
                self.bot.cd.add(ctx.author.id)
            else:
                if str(reaction.emoji) == "<:blorplecross:436007034832551938>":
                    embed.set_author(name="Edit cancelled.")
                    self.bot.cd.add(ctx.author.id)
                else:
                    colour = reaction.emoji.name.replace("pl_", "")

        if colour:
            colours = []
            if str(ctx.guild.id) in self.bot.partners.keys():
                colours.append(self.bot.partners[str(ctx.guild.id)]['tag'])
            colours += [
                name for name, emoji in self.bot.colours.items()
                if name not in ['edit']
            ]

            if colour not in colours and self.bot.partnercolourlock:
                return await ctx.send(f"{ctx.author.mention}, that colour is not available within this server!")

            olddata = copy.copy(board.data[str(y)][str(x)])

            # board.data[str(y)][str(x)] = {
            #     "c": colour,
            #     # "info": olddata['info'] + [{
            #     #     "user": ctx.author.id,
            #     #     "time": datetime.datetime.utcnow()
            #     # }]
            # }
            board.data[str(y)][str(x)] = colour
            await self.history(board, colour, ctx.author.id, (x, y))
            embed.set_author(name="Pixel successfully set.")
            success = True


        loc, emoji, raw, zoom = self.screen(board, x, y)

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

        await msg.edit(content=display, embed=embed)
        await msg.clear_reactions()

        if success:
            member = await ctx.bot.blurpleguild.fetch_member(ctx.author.id)
            if member and self.bot.artistrole not in [i.id for i in member.roles]:
                await member.add_roles(ctx.bot.blurpleguild.get_role(self.bot.artistrole))
                # t = ""
                # if ctx.author.guild.id != ctx.bot.blurpleguild.id: t = " in the Project Blurple server"
                # await ctx.send(f"{ctx.author.mention}, that was your first pixel placed! For that, you have received the **Artist** role{t}!")
                await ctx.send(f"{ctx.author.mention}, that was your first pixel placed! For that, you have received the **Artist** role{' in the Project Blurple server' if ctx.author.guild.id != ctx.bot.blurpleguild.id else ''}!")

        await self.bot.dbs.boards[board.name.lower()].update_one({'row': y}, {'$set': {str(y): board.data[str(y)]}})
        await self.bot.dbs.boards[board.name.lower()].update_one({'type': 'history'}, {'$set': {'history': board.history}})

    @commands.command()
    @executive()
    async def paste(self, ctx, x: int, y: int, source = None):
        board = await self.findboard(ctx)
        if not board: return

        if board.locked == True:
            return await ctx.send(f'{ctx.author.mention}, this board is locked (view only)')

        empty = '----'

        if ctx.message.attachments:
            arraywh = await self.bot.loop.run_in_executor(None, self.pastefrombytes, io.BytesIO(await ctx.message.attachments[0].read()))
            if isinstance(arraywh, str): return await ctx.send(f"{ctx.author.mention}, {arraywh}")
            else: array, width, height = arraywh

        elif source:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(source) as r:
                    raw = await r.text()

            rows = raw.split('\n')
            array = [i.split() for i in rows]

            width = len(sorted(array, key = len, reverse = True)[0])
            height = len(array)

            colours = [v['tag'] for v in self.bot.partners.values()] + [name for name, emoji in self.bot.colours.items() if name not in ['edit']] + [empty]

            if any([any([not v in colours for v in r]) for r in array]):
                return await ctx.send(f"{ctx.author.mention}, the source paste that you linked does not appear to be valid.")

        if board.width - x + 1 < width or board.height - y + 1 < height:
            return await ctx.send(f"{ctx.author.mention}, the paste does not appear to fit. Please make sure you are selecting the pixel position of the top-left corner of the paste.")

        for row, i in enumerate(array):
            for n, pixel in enumerate(i):
                if pixel == empty: continue
                board.data[str(y + row)][str(x + n)] = pixel

                await self.history(board, pixel, ctx.author.id, (x + n, y + n))

        await ctx.send(f"{ctx.author.mention}, pasted!")

        for row, i in enumerate(array):
            await self.bot.dbs.boards[board.name.lower()].update_one({'row': y + row}, {'$set': {str(y + row): board.data[str(y + row)]}})
        await self.bot.dbs.boards[board.name.lower()].update_one({'type': 'history'}, {'$set': {'history': board.history}})


    def pastefrombytes(self, imgbytes):
        image = Image.open(imgbytes, 'r')
        # image = Image.open("canvaspastetest.png", "r")
        width, height = image.size
        pixel_values = list(image.getdata())
        
        channels = 4

        pixel_values = numpy.array(pixel_values).reshape((width, height, channels))


        colours = {**{v['rgb'][:3]: v['tag'] for v in self.bot.partners.values()}, **{v['rgb'][:3]: v['tag'] for v in self.bot.coloursdict.values() if v['tag'] not in ['edit', 'blank']}}

        empty = '----'

        array = []
        for row, i in enumerate(pixel_values):
            array.append([])
            for n, pixel in enumerate(i):
                if len(pixel) == 4:
                    if pixel[3] == 0:
                        array[row].append(empty)
                        continue
                
                p = tuple(pixel[:3])
                if p not in colours.keys(): return f"invalid pixel at ({n+1}, {row+1})"
                
                array[row].append(colours[p])

        return array, width, height

    @commands.command(aliases = ['colors'])
    async def colours(self, ctx, palettes = 'all'):
        """Shows the full colour palette available. Type 'main' or 'partner' after the command to see a specific group of colours."""
        palettes = palettes.lower()
        if palettes in ['main', 'default']: palettes = 'main'
        elif palettes in ['partner', 'partners']: palettes = 'partner'
        else: palettes = 'all'

        image = discord.File(fp = copy.copy(self.bot.colourimg[palettes]), filename = "Blurple_Canvas_Colour_Palette.png")
        
        embed = discord.Embed(
            title="Blurple Canvas Colour Palette", colour=0x7289da, timestamp=datetime.datetime.utcnow())
        embed.set_footer(
            text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
            icon_url=self.bot.user.avatar_url)
        embed.set_image(url = "attachment://Blurple_Canvas_Colour_Palette.png")
        await ctx.send(embed=embed, file=image)

    @commands.command(aliases = ['reloadcolors'])
    @admin()
    async def reloadcolours(self, ctx):
        self.bot.colourimg = {
            x: await self.bot.loop.run_in_executor(None, self.image.colours, self, x) for x in ['all', 'main', 'partner']
        }
        await ctx.send("Done")

    @commands.command(aliases=['tpcel'])
    @executive()
    async def togglepartnercolourexclusivitylock(self, ctx):
        self.bot.partnercolourlock = not self.bot.partnercolourlock
        await ctx.send(f"Set the partner colour exclusivity lock to {self.bot.partnercolourlock}")

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

    @commands.command(hidden = True)
    async def test(self, ctx):
        print([guild.name for guild in self.bot.guilds])

    @commands.command(name="viewnh", aliases=["seenh"])
    @commands.cooldown(1, 30, BucketType.user)
    @inteam()
    async def viewnh(self, ctx, *, xyz: coordinates = None):
        """Views a section of the board as an image. Must have xy coordinates, zoom (no. of tiles wide) optional."""
        board = await self.findboard(ctx)
        if not board: return

        if not xyz: return await ctx.send(f'{ctx.author.mention}, please specify coordinates (e.g. `234 837` or `12 53`)')

        x, y, zoom = xyz

        if board.data == None:
            return await ctx.send('{ctx.author.mention}, there is currently no board created')

        if x < 1 or x > board.width or y < 1 or y > board.height:
            return await ctx.send(
                f'{ctx.author.mention}, please send coordinates between (1, 1) and ({board.width}, {board.height})'
            )

        defaultzoom = 25

        if zoom == None or zoom > board.width or zoom > board.height:
            zoom = defaultzoom
        if zoom > board.width or zoom > board.height:
            if board.width > board.height: zoom = board.width
            else: zoom = board.height
        if zoom < 5:
            return await ctx.send(f'{ctx.author.mention}, please have a minumum zoom of 5 tiles')

        async with aiohttp.ClientSession() as session:
            async with ctx.typing():
                start = time.time()
                image = await self.bot.loop.run_in_executor(
                    None, self.image.imager, self, board, x, y, zoom, False)
                end = time.time()
                image = discord.File(fp=image, filename=f'board_{x}-{y}.png')

                embed = discord.Embed(
                    colour=0x7289da, timestamp=datetime.datetime.utcnow())
                embed.set_author(name=f"{board.name} | Image took {end - start:.2f}s to load")
                embed.set_footer(
                    text=f"{str(ctx.author)} | {self.bot.user.name} | {ctx.prefix}{ctx.command.name}",
                    icon_url=self.bot.user.avatar_url)
                embed.set_image(url=f"attachment://board_{x}-{y}.png")
                await ctx.send(embed=embed, file=image)

def setup(bot):
    bot.add_cog(CanvasCog(bot))