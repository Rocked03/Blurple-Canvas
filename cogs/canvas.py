import aiohttp, asyncio, datetime, discord, io, math, motor.motor_asyncio, PIL, pymongo, random, sys, time, traceback, typing
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from PIL import Image, ImageDraw, ImageFont
# pillow, motor, pymongo, discord.py


def dev():
    async def pred(ctx):
        return ctx.author.id in ctx.bot.allowedusers

    return commands.check(pred)


def inteam():
    async def pred(ctx): 
        # return True
        a = any(elem in [v for k, v in ctx.bot.teams.items()] for elem in [i.id for i in ctx.bot.blurpleguild.get_member(ctx.author.id).roles]) 
        if not a: ctx.bot.cd.add(ctx.author.id)
        return a
    return commands.check(pred)


def mod():
    async def pred(ctx): return any(elem in [v for k, v in ctx.bot.modroles.items()] for elem in [i.id for i in ctx.bot.blurpleguild.get_member(ctx.author.id).roles])
    return commands.check(pred)

def admin():
    # async def pred(ctx): return any(elem in [v for k, v in ctx.bot.modroles.items() if k == "Admin"] for elem in [i.id for i in ctx.bot.blurpleguild.get_member(ctx.author.id).roles])
    async def pred(ctx): return ctx.bot.modroles['Admin'] in [i.id for i in ctx.bot.blurpleguild.get_member(ctx.author.id).roles]
    return commands.check(pred)


class CanvasCog(commands.Cog, name="Canvas"):
    """Canvas Module"""

    def __init__(self, bot):
        self.bot = bot

        self.bot.initfinished = False

        self.bot.modroles = {
            "Admin":       443013283977494539,
            "Executive":   413213839866462220,
            "Moderator":   569015549225598976,
            "Helper":      442785212502507551,
        }

        self.bot.cd = set()

        # self.bot.teams = {
        #     "light": 573011450231259157,
        #     "dark": 573011441683005440,
        # }
        self.bot.teams = {"blurple user": 705295796773584976}

        self.bot.artistrole = 705295638216048681

        self.bot.skipconfirm = []

        self.bot.uboards = {}

        self.bot.boards = dict()


        self.bot.pymongo = motor.motor_asyncio.AsyncIOMotorClient("mongodb+srv://Rocked03:qKuAVNAqCH7fZVpx@blurple-canvas-lj40x.mongodb.net/test?retryWrites=true")
        self.bot.pymongoog = pymongo.MongoClient("mongodb+srv://Rocked03:qKuAVNAqCH7fZVpx@blurple-canvas-lj40x.mongodb.net/test?retryWrites=true")

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
                    if name == 'main2019': continue
                    board = self.bot.pymongoog.boards[name]
                    info = (board.find_one({'type': 'info'}))['info']
                    data = list(board.find({'type': 'data'}))
                    d = {k: v for d in data for k, v in d.items()}
                    self.bot.boards[info['name'].lower()] = self.board(name = info['name'], width = info['width'], height = info['height'], locked = info['locked'], data = d)

                    print(f"Loaded '{name}'")
                print('All boards loaded')

            some_stuff = await bot.loop.run_in_executor(None, loadboards, self)

        self.bot.loop.create_task(getboards(self))

        self.bot.initfinished = True


    class board():
        def __init__(self, *, name, width, height, locked, data = dict()):
            self.data = data
            self.name = name
            self.width = width
            self.height = height
            self.locked = locked

    class image():
        fontxy = ImageFont.truetype("Uni Sans Heavy.otf", 60)
        fonttitle = ImageFont.truetype("Uni Sans Heavy.otf", 18)
        fontcoordinates = ImageFont.truetype("Uni Sans Heavy.otf", 21)

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
                    width=1)  # Hightlight y

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

    @commands.Cog.listener()  # Error Handler
    async def on_command_error(self, ctx, error):
        ignored = (commands.CommandNotFound, commands.UserInputError)
        if isinstance(error, ignored): return

        if isinstance(error, commands.CheckFailure):
            await ctx.send(f"{ctx.author.mention}, It doesn't look like you are allowed to run this command. Make sure you've got the Blurple User role in the main server, otherwise these commands will not work!")
            return

        if isinstance(error, commands.CommandOnCooldown):
            if 706475186274172989 in [role.id for role in ctx.author.roles]:
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

        demoji = []
        draw = []
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
                        de.append("<:" + pt[pixel["c"]] + ">")
                        dr.append(pixel["c"])
                if dr:
                    demoji.append(de)
                    draw.append(dr)

        return loc, demoji, draw, zoom

    class boardspec(commands.Converter):
        async def convert(self, ctx, seed):
            options = ['random']
            if seed.lower() in [i.lower() for i in options]:
                return seed.lower()
            else:
                raise Exception

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
                    newboard.data[str(yn)][str(xn)] = {
                        "c":
                            random.choice([
                                name for name in self.bot.colours.keys()
                                if name not in ['edit', 'blank']
                            ]),
                        "info": {
                            "user": "Automatic",
                            "time": datetime.datetime.utcnow()
                        }
                    }
                else:
                    newboard.data[str(yn)][str(xn)] = {
                        "c": "blank",
                        "info": {
                            "user": "Automatic",
                            "time": datetime.datetime.utcnow()
                        }
                    }

        await ctx.send("Created board, saving to database")

        await self.bot.dbs.boards.create_collection(newboard.name.lower())
        dboard = self.bot.dbs.boards.get_collection(newboard.name.lower())
        await dboard.insert_many([{'type': 'info', 'info': {'name': newboard.name, 'width': newboard.width, 'height': newboard.height, 'locked': False}}])

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
            await ctx.send(
                f"You haven't joined a board! Type `{ctx.prefix}join <board>` to join a board! To see all boards, type `{ctx.prefix}boards`"
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
    @commands.cooldown(1, 30, BucketType.user)
    @inteam()
    async def view(self, ctx, *, xyz: coordinates = None):
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
                    None, self.image.imager, self, board, x, y, zoom)
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
                for future in pending:
                    future.cancel()
                return
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
    @commands.cooldown(1, 45, BucketType.user)  # 1 msg per 45s
    async def place(self, ctx, *, xyz: coordinates(True) = None):
        """Places a tile at specified location. Must have xy coordinates. Same inline output as viewnav. Choice to reposition edited tile before selecting colour. Cooldown of 5 minutes per tile placed."""
        board = await self.findboard(ctx)

        if board.locked == True:
            return await ctx.send(f'{ctx.author.mention}, this board is locked (view only)')
        
        if ctx.author in self.bot.cd: self.bot.cd.remove(ctx.author.id)

        if not board: 
            self.bot.cd.add(ctx.author.id)
            return

        if not xyz: 
            self.bot.cd.add(ctx.author.id)
            return await ctx.send(f'{ctx.author.mention}, please specify coordinates (e.g. `234 837` or `12 53`')

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

        if colour.lower() in [i for i in self.bot.colours.keys() if i not in ['blank', 'edit']] + [i['tag'] for i in self.bot.partners.values()]:
            colour = colour.lower()
        else: colour = None

        cllist = {}
        for k, v in self.bot.partners.items():
            cllist[v['tag']] = v['emoji']
        for k, v in self.bot.colours.items():
            cllist[k] = v

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
                    await msg.clear_reactions()
                    self.bot.cd.add(ctx.author.id)
                    for future in pending:
                        future.cancel()
                    return
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
            if ctx.guild.id in self.bot.partners.keys():
                colours.append(self.bot.partners[ctx.guild.id]['emoji'])
            dcolours = [
                name for name, emoji in self.bot.colours.items()
                if name not in ['edit', 'blank']
            ]
            l = ['brll', 'hpsq', 'bhnt', 'blnc', 'ptnr', 'devl', 'blpl', 'dbpl', 'brvy', 'bstp', 'whte', 'ntgr', 'grpl', 'ntbl', 'dgry', 'nqbl']
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
            if ctx.guild.id in self.bot.partners.keys():
                colours.append(self.bot.partners[ctx.guild.id]['tag'])
            colours += [
                name for name, emoji in self.bot.colours.items()
                if name not in ['edit', 'blank']
            ]

            if colour not in colours:
                return await ctx.send(f"{ctx.author.mention}, that colour is not available within this server!")


            board.data[str(y)][str(x)] = {
                "c": colour,
                "info": {
                    "user": ctx.author.id,
                    "time": datetime.datetime.utcnow()
                }
            }
            embed.set_author(name="Pixel successfully set.")


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

        member = ctx.bot.blurpleguild.get_member(ctx.author.id)
        if self.bot.artistrole not in [i.id for i in member.roles]:
            await member.add_roles(ctx.bot.blurpleguild.get_role(self.bot.artistrole))
            t = ""
            if ctx.author.guild.id != ctx.bot.blurpleguild.id: t = " in the Project Blurple server"
            await ctx.send(f"{ctx.author.mention}, that was your first pixel placed! For that, you have received the **Artist** role{t}!")

        await self.bot.dbs.boards[board.name.lower()].update_one({'row': y}, {'$set': {str(y): board.data[str(y)]}})

    @commands.command()
    @dev()
    async def debugraw(self, ctx):
        board = await self.findboard(ctx)
        if not board: return

        print(board.data)
        print([[xv["c"] for xv in xk.values()]
               for xk in board.data.values()])
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