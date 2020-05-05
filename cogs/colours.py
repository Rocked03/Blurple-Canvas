from discord.ext import commands
import pymongo

def dev():
    async def pred(ctx):
        return ctx.author.id in ctx.bot.allowedusers

    return commands.check(pred)

class ColoursCog(commands.Cog, name="Colours"):

    def __init__(self, bot):
        self.bot = bot

        a = pymongo.MongoClient("mongodb+srv://Rocked03:qKuAVNAqCH7fZVpx@blurple-canvas-lj40x.mongodb.net/test?retryWrites=true")
        self.colourscoll = a.colours

        self.bot.colours, self.bot.coloursrgb = self.defaultcolours()
        self.bot.empty = "<:empty:541914164235337728>"
        self.bot.partners = self.partnercolours()


    def defaultcolours(self):
        mydict = self.colourscoll.default

        c = {}
        crgb = {}
        for i in mydict.find():
            c[i['code']] = i['emoji']
            if i['code'] != "edit":
                crgb[i['code']] = tuple(i['rgb'])

        return c, crgb

    def partnercolours(self):
        mydict = self.colourscoll.partner

        c = {}
        for i in mydict.find():
            c[i['guild']] = {
                "name": i['name'],
                "tag": i['tag'],
                "emoji": i['emoji'],
                "guild": i['guild'],
                "rgb": tuple(i['rgb']),
            }

        return c

    @commands.command(name="addpcolour")
    @dev()
    async def addpcolour(self, ctx, guildid, tag, emoji, rgb, *, name):
        """Adds a new partner colour to the list"""
        try:
            rgbformatted = tuple([int(i) for i in rgb.split(',')] + [255])
            if len(rgbformatted) != 4: raise Exception('no')
        except Exception as e:
            return await ctx.send('Not correct rgb formatting - type `R,G,B` (not `(R, G, B)`)')

        mydict = {
            "name": name,
            "tag": tag,
            "emoji": emoji[2:][:-1],
            "guild": int(guildid),
            "rgb": rgbformatted
        }

        await ctx.send('Is this what you want to add? (yes/no)\n' + str(mydict))

        def check(message):
            return ctx.author == message.author and message.content.lower() in ['yes', 'no', 'y', 'n'] and message.channel == ctx.message.channel

        msg = await self.bot.wait_for('message', check=check)
        
        if msg.content in ['no', 'n']:
            return await ctx.send("Ok, cancelled")

        self.colourscoll.partner.insert_many([mydict])
        self.bot.partners = self.partnercolours()
        await ctx.send("Ok, done.")

    @commands.command(hidden = True)
    @dev()
    async def server(self, ctx):
        for s in await self.bot.fetch_guilds(limit=None).flatten():
            print(f"{str(s)} ({s.id})")

    @commands.command(hidden = True)
    @dev()
    async def servertest(self, ctx):
        channel = ctx.guild.get_channel(573546839085940751)

        i = 0
        async for m in channel.history(limit=None):
            i += 1
            if m.author.id == 420675394224521240:
                e = m.embeds[0]
                f = e.fields[0]
                if int(f.value) > 4000:
                    print(f"{e.author.name} - {f.value}")

    # @commands.command()
    # @dev()
    # async def role2019(self, ctx):
    #     lrole = ctx.guild.get_role(573011450231259157)
    #     drole = ctx.guild.get_role(573011441683005440)
    #     nrole = ctx.guild.get_role(705294465631256607)

    #     i = 0
    #     for u in ctx.guild.members:
    #         if (lrole in u.roles or drole in u.roles) and nrole not in u.roles:
    #             await u.add_roles(nrole)
    #             i += 1
    #             print(f"Added to {str(u)}")

    #     await ctx.send(f'Done ({i} users!)')


        # self.bot.colours = {
        #     "brll": "pl_brll:541841828844929025",  # Brilliance Red
        #     "hpsq": "pl_hpsq:541841829969133571",  # Hypesquad Yellow
        #     "bhnt": "pl_bhnt:541841828454858801",  # Bug Hunter Green
        #     "blnc": "pl_blnc:541841828652122133",  # Balance Cyan
        #     "ptnr": "pl_ptnr:541841829679857664",  # Partner Blue
        #     "blpl": "pl_blpl:540761785884737537",  # Blurple
        #     "brvy": "pl_brvy:541841829256101899",  # Bravery Purple
        #     "whte": "pl_whte:546829770055352340",  # Full White
        #     "ntgr": "pl_ntgr:541841829520211968",  # Nitro Grey
        #     "grpl": "pl_grpl:541841829453103142",  # Greyple
        #     "ntbl": "pl_ntbl:541841829318885396",  # Nitro Blue
        #     "nqbl": "pl_nqbl:546829770030317569",  # Not Quite Black
        #     "blank": "pl_blank:540761786484391957",  # Blank tile
        #     "edit": "pl_edit:540761787662991370"  # Edit tile
        # }
        # self.bot.coloursrgb = {
        #     "brll": (244, 123, 103, 255),
        #     "hpsq": (248, 165, 50, 255),
        #     "bhnt": (72, 183, 132, 255),
        #     "blnc": (69, 221, 192, 255),
        #     "ptnr": (65, 135, 237, 255),
        #     "blpl": (114, 137, 218, 255),p/
        #     "brvy": (156, 132, 239, 255),
        #     "whte": (255, 255, 255, 255),
        #     "ntgr": (183, 194, 206, 255),
        #     "grpl": (153, 170, 181, 255),
        #     "ntbl": (79, 93, 127, 255),
        #     "nqbl": (44, 47, 51, 255),
        #     "blank": (114, 137, 218, 127),
        # }
        # self.bot.empty = "<:empty:541914164235337728>"
 
        # self.bot.partners = {
        #     281648235557421056: { # r/Marvel Discord
        #         "name": "Marvel Red",
        #         "tag": "mrvl",
        #         "emoji": "pl_mrvl:572564652559564810",
        #         "guild": 281648235557421056,
        #         "rgb": (234, 35, 40, 255),
        #     },
        #     272885620769161216: { # Blob Emoji
        #         "name": "Blob Yellow",
        #         "tag": "blob",
        #         "emoji": "pl_blob:573101758130421770",
        #         "guild": 272885620769161216,
        #         "rgb": (252, 194, 27, 255),
        #     },
        #     316720611453829121: { # N.I.T.R.O.
        #         "name": "N.I.T.R.O. Orange",
        #         "tag": "ntro",
        #         "emoji": "pl_ntro:575279584820330498",
        #         "guild": 316720611453829121,
        #         "rgb": (252, 150, 75, 255)
        #     },
        #     152517096104919042: { # Rocket League
        #         "name": "Rocketeer Blue",
        #         "tag": "rckt",
        #         "emoji": "pl_rckt:574086064671555624",
        #         "guild": 152517096104919042,
        #         "rgb": (0, 156, 222, 255),
        #     },
        #     290572012437372931: { # Ping and Salar
        #         "name": "Ping and Salar's Red",
        #         "tag": "pgsl",
        #         "emoji": "pl_pgsl:574086064827007027",
        #         "guild": 290572012437372931,
        #         "rgb": (255, 64, 0, 255),
        #     },
        #     349243932447604736: { # r/Jailbreak
        #         "name": "Cydia Brown",
        #         "tag": "jlbr",
        #         "emoji": "pl_jlbr:574086064923475988",
        #         "guild": 349243932447604736,
        #         "rgb": (165, 107, 77, 255),
        #     },
        #     173184118492889089: { # Tatsumaki
        #         "name": "Tatsu Emerald",
        #         "tag": "ttsu",
        #         "emoji": "pl_ttsu:574907457995014154",
        #         "guild": 173184118492889089,
        #         "rgb": (23, 161, 103, 255),
        #     },
        #     262077211526299648: { # Auttaja
        #         "name": "Auttaja Blue",
        #         "tag": "attj",
        #         "emoji": "pl_attj:574907457915060224",
        #         "guild": 262077211526299648,
        #         "rgb": (0, 112, 250, 255),
        #     },
        #     228406572756369408: { # r/StarWars
        #         "name": "Opening Crawl Yellow",
        #         "tag": "stwr",
        #         "emoji": "pl_stwr:575279585130840102",
        #         "guild": 228406572756369408,
        #         "rgb": (254, 210, 24, 255),
        #     },
        #     145166056812576768: { # Ayana
        #         "name": "Ayana Pink",
        #         "tag": "ayna",
        #         "emoji": "pl_ayna:575452605292216340",
        #         "guild": 145166056812576768,
        #         "rgb": (198, 59, 104, 255),
        #     },
        #     284447205358829570: { # The Furry Nexus
        #         "name": "Paw Print Pink",
        #         "tag": "frry",
        #         "emoji": "pl_frry:575567782683607040",
        #         "guild": 284447205358829570,
        #         "rgb": (198, 118, 255, 255)
        #     },
        #     304383757975289857: { # Blob Hub
        #         "name": "Butterfly Pink",
        #         "tag": "nbhb",
        #         "emoji": "pl_nbhb:575636279383949312",
        #         "guild": 304383757975289857,
        #         "rgb": (233, 160, 214, 255),
        #     },
        #     416749164731301888: { # PUBG
        #         "name": "Winner Winner Golden Dinner",
        #         "tag": "pubg",
        #         "emoji": "pl_pubg:575808438114844682",
        #         "guild": 416749164731301888,
        #         "rgb": (222, 141, 0, 255)
        #     },
        #     478114566509821953: { # r/Google
        #         "name": "Google Yellow",
        #         "tag": "goog",
        #         "emoji": "pl_goog:576591834529267732",
        #         "guild": 478114566509821953,
        #         "rgb": (251, 188, 5, 255),
        #     },
        #     # 360462032811851777: { # Something For Everybody
        #     #     "name": "",
        #     #     "tag": "sfeb",
        #     #     "emoji": "pl_sfeb:",
        #     #     "guild": 360462032811851777,
        #     #     "rgb": ()
        #     # },
        #     493351982887862283: { # Pepe Emoji
        #         "name": "Pepe Green",
        #         "tag": "pepe",
        #         "emoji": "pl_pepe:577471090973212683",
        #         "guild": 493351982887862283,
        #         "rgb": (91, 144, 66, 255),
        #     },
        #     446658603873730611: { # Raft
        #         "name": "Raft Blue",
        #         "tag": "raft",
        #         "emoji": "pl_raft:577597652573749248",
        #         "guild": 446658603873730611,
        #         "rgb": (68, 174, 210, 255),
        #     }
        # }

def setup(bot):
    bot.add_cog(ColoursCog(bot))