from discord.ext import commands

class ColoursCog(commands.Cog, name="Colours"):

    def __init__(self, bot):
        self.bot = bot

        self.bot.colours = {
            "brll": "pl_brll:541841828844929025",  # Brilliance Red
            "hpsq": "pl_hpsq:541841829969133571",  # Hypesquad Yellow
            "bhnt": "pl_bhnt:541841828454858801",  # Bug Hunter Green
            "blnc": "pl_blnc:541841828652122133",  # Balance Cyan
            "ptnr": "pl_ptnr:541841829679857664",  # Partner Blue
            "blpl": "pl_blpl:540761785884737537",  # Blurple
            "brvy": "pl_brvy:541841829256101899",  # Bravery Purple
            "whte": "pl_whte:546829770055352340",  # Full White
            "ntgr": "pl_ntgr:541841829520211968",  # Nitro Grey
            "grpl": "pl_grpl:541841829453103142",  # Greyple
            "ntbl": "pl_ntbl:541841829318885396",  # Nitro Blue
            "nqbl": "pl_nqbl:546829770030317569",  # Not Quite Black
            "blank": "pl_blank:540761786484391957",  # Blank tile
            "edit": "pl_edit:540761787662991370"  # Edit tile
        }
        self.bot.coloursrgb = {
            "brll": (244, 123, 103, 255),
            "hpsq": (248, 165, 50, 255),
            "bhnt": (72, 183, 132, 255),
            "blnc": (69, 221, 192, 255),
            "ptnr": (65, 135, 237, 255),
            "blpl": (114, 137, 218, 255),
            "brvy": (156, 132, 239, 255),
            "whte": (255, 255, 255, 255),
            "ntgr": (183, 194, 206, 255),
            "grpl": (153, 170, 181, 255),
            "ntbl": (79, 93, 127, 255),
            "nqbl": (44, 47, 51, 255),
            "blank": (114, 137, 218, 127),
        }
        self.bot.empty = "<:empty:541914164235337728>"
 
        self.bot.partners = {
            281648235557421056: { # r/Marvel Discord
                "name": "Marvel Red",
                "tag": "mrvl",
                "emoji": "pl_mrvl:572564652559564810",
                "guild": 281648235557421056,
                "rgb": (234, 35, 40, 255),
            },
            272885620769161216: { # Blob Emoji
                "name": "Blob Yellow",
                "tag": "blob",
                "emoji": "pl_blob:573101758130421770",
                "guild": 272885620769161216,
                "rgb": (252, 194, 27, 255),
            },
            316720611453829121: { # N.I.T.R.O.
                "name": "N.I.T.R.O. Orange",
                "tag": "ntro",
                "emoji": "pl_ntro:575279584820330498",
                "guild": 316720611453829121,
                "rgb": (252, 150, 75, 255)
            },
            152517096104919042: { # Rocket League
                "name": "Rocketeer Blue",
                "tag": "rckt",
                "emoji": "pl_rckt:574086064671555624",
                "guild": 152517096104919042,
                "rgb": (0, 156, 222, 255),
            },
            290572012437372931: { # Ping and Salar
                "name": "Ping and Salar's Red",
                "tag": "pgsl",
                "emoji": "pl_pgsl:574086064827007027",
                "guild": 290572012437372931,
                "rgb": (255, 64, 0, 255),
            },
            349243932447604736: { # r/Jailbreak
                "name": "Cydia Brown",
                "tag": "jlbr",
                "emoji": "pl_jlbr:574086064923475988",
                "guild": 349243932447604736,
                "rgb": (165, 107, 77, 255),
            },
            173184118492889089: { # Tatsumaki
                "name": "Tatsu Emerald",
                "tag": "ttsu",
                "emoji": "pl_ttsu:574907457995014154",
                "guild": 173184118492889089,
                "rgb": (23, 161, 103, 255),
            },
            262077211526299648: { # Auttaja
                "name": "Auttaja Blue",
                "tag": "attj",
                "emoji": "pl_attj:574907457915060224",
                "guild": 262077211526299648,
                "rgb": (0, 112, 250, 255),
            },
            228406572756369408: { # r/StarWars
                "name": "Opening Crawl Yellow",
                "tag": "stwr",
                "emoji": "pl_stwr:575279585130840102",
                "guild": 228406572756369408,
                "rgb": (254, 210, 24, 255),
            },
            145166056812576768: { # Ayana
                "name": "Ayana Pink",
                "tag": "ayna",
                "emoji": "pl_ayna:575452605292216340",
                "guild": 145166056812576768,
                "rgb": (198, 59, 104, 255),
            },
            284447205358829570: { # The Furry Nexus
                "name": "Paw Print Pink",
                "tag": "frry",
                "emoji": "pl_frry:575567782683607040",
                "guild": 284447205358829570,
                "rgb": (198, 118, 255, 255)
            },
            304383757975289857: { # Blob Hub
                "name": "Butterfly Pink",
                "tag": "nbhb",
                "emoji": "pl_nbhb:575636279383949312",
                "guild": 304383757975289857,
                "rgb": (233, 160, 214, 255),
            },
        }

def setup(bot):
    bot.add_cog(ColoursCog(bot))