"""
Crypto Symbol Configuration
===========================
Centralized, configurable mapping of crypto symbols to their English and Persian names.

Symbols are synced from Toobit exchange (535 active spot trading pairs).
To refresh, fetch from GET https://api.toobit.com/api/v1/exchangeInfo

Usage:
    from crypto_symbols import resolve_symbol, get_valid_symbols, get_news_valid_symbols

    resolved = resolve_symbol("بیت‌کوین")  # Returns "BTC"
    resolved = resolve_symbol("bitcoin")   # Returns "BTC"
    resolved = resolve_symbol("BTC")       # Returns "BTC"
    resolved = resolve_symbol("invalid")   # Returns None

    # Resolve a symbol name that appears inside a sentence:
    resolved = resolve_symbol_contained("give me eth")        # Returns "ETH"
    resolved = resolve_symbol_contained("تحلیل اتریوم")        # Returns "ETH"
"""

import re

# =========================================================================
# CONFIGURATION: Add/remove symbols here
# Synced from Toobit exchange - 535 active spot trading pairs
# =========================================================================

CRYPTO_SYMBOLS = {
    "1INCH": {
        "english_name": "1inch",
        "persian_names": ['وان اینچ', '1 اینچ'],
    },
    "2Z": {
        "english_name": "2Z",
        "persian_names": [],
    },
    "4": {
        "english_name": "4",
        "persian_names": [],
    },
    "A": {
        "english_name": "A",
        "persian_names": [],
    },
    "A8": {
        "english_name": "A8",
        "persian_names": [],
    },
    "AAPLON": {
        "english_name": "AAPLON",
        "persian_names": [],
    },
    "AAVE": {
        "english_name": "Aave",
        "persian_names": ["آوه", "اوه"],
    },
    "ACE": {
        "english_name": "ACE",
        "persian_names": [],
    },
    "ACH": {
        "english_name": "ACH",
        "persian_names": [],
    },
    "ACM": {
        "english_name": "ACM",
        "persian_names": [],
    },
    "ACT": {
        "english_name": "ACT",
        "persian_names": [],
    },
    "ACX": {
        "english_name": "ACX",
        "persian_names": [],
    },
    "ADA": {
        "english_name": "Cardano",
        "persian_names": ["کاردانو", "ادا"],
    },
    "ADX": {
        "english_name": "ADX",
        "persian_names": [],
    },
    "AERO": {
        "english_name": "AERO",
        "persian_names": [],
    },
    "AEVO": {
        "english_name": "AEVO",
        "persian_names": [],
    },
    "AGI": {
        "english_name": "AGI",
        "persian_names": [],
    },
    "AIA": {
        "english_name": "AIA",
        "persian_names": [],
    },
    "AIGENSYN": {
        "english_name": "AIGENSYN",
        "persian_names": [],
    },
    "AIN": {
        "english_name": "AIN",
        "persian_names": [],
    },
    "AIO": {
        "english_name": "AIO",
        "persian_names": [],
    },
    "AIXBT": {
        "english_name": "AIXBT",
        "persian_names": [],
    },
    "AKE": {
        "english_name": "AKE",
        "persian_names": [],
    },
    "ALCH": {
        "english_name": "ALCH",
        "persian_names": [],
    },
    "ALCX": {
        "english_name": "ALCX",
        "persian_names": [],
    },
    "ALGO": {
        "english_name": "Algorand",
        "persian_names": ['الگوراند', 'آلگوراند'],
    },
    "ALICE": {
        "english_name": "ALICE",
        "persian_names": [],
    },
    "ALLO": {
        "english_name": "ALLO",
        "persian_names": [],
    },
    "ALMANAK": {
        "english_name": "ALMANAK",
        "persian_names": [],
    },
    "AMDB": {
        "english_name": "AMDB",
        "persian_names": [],
    },
    "AMP": {
        "english_name": "AMP",
        "persian_names": [],
    },
    "AMZNX": {
        "english_name": "AMZNX",
        "persian_names": [],
    },
    "ANIME": {
        "english_name": "ANIME",
        "persian_names": [],
    },
    "ANKR": {
        "english_name": "ANKR",
        "persian_names": [],
    },
    "ANOME": {
        "english_name": "ANOME",
        "persian_names": [],
    },
    "APE": {
        "english_name": "ApeCoin",
        "persian_names": ['ایپ کوین', 'ایپ\u200cکوین'],
    },
    "API3": {
        "english_name": "API3",
        "persian_names": [],
    },
    "APR": {
        "english_name": "APR",
        "persian_names": [],
    },
    "APT": {
        "english_name": "Aptos",
        "persian_names": ["آپتوس"],
    },
    "ARB": {
        "english_name": "Arbitrum",
        "persian_names": ['آربیتروم', 'آربیترم'],
    },
    "ARG": {
        "english_name": "ARG",
        "persian_names": [],
    },
    "ARIA": {
        "english_name": "ARIA",
        "persian_names": [],
    },
    "ARKM": {
        "english_name": "Arkham",
        "persian_names": ['آرکهام'],
    },
    "ARPA": {
        "english_name": "ARPA",
        "persian_names": [],
    },
    "ARTX": {
        "english_name": "ARTX",
        "persian_names": [],
    },
    "ARX": {
        "english_name": "ARX",
        "persian_names": [],
    },
    "ASP": {
        "english_name": "ASP",
        "persian_names": [],
    },
    "ASR": {
        "english_name": "ASR",
        "persian_names": [],
    },
    "ASTER": {
        "english_name": "ASTER",
        "persian_names": [],
    },
    "AT": {
        "english_name": "AT",
        "persian_names": [],
    },
    "ATH": {
        "english_name": "ATH",
        "persian_names": [],
    },
    "ATM": {
        "english_name": "ATM",
        "persian_names": [],
    },
    "ATOM": {
        "english_name": "Cosmos",
        "persian_names": ['کازماس', 'اتم'],
    },
    "AUDIO": {
        "english_name": "Audius",
        "persian_names": ['آدیوس'],
    },
    "AVA": {
        "english_name": "AVA",
        "persian_names": [],
    },
    "AVAX": {
        "english_name": "Avalanche",
        "persian_names": ["آوالانچ", "آوا لانچ", "اوالانچ"],
    },
    "AVL": {
        "english_name": "AVL",
        "persian_names": [],
    },
    "AVNT": {
        "english_name": "AVNT",
        "persian_names": [],
    },
    "AWE": {
        "english_name": "AWE",
        "persian_names": [],
    },
    "AXL": {
        "english_name": "AXL",
        "persian_names": [],
    },
    "AXS": {
        "english_name": "Axie Infinity",
        "persian_names": ['اکسی اینفینیتی', 'اکسی'],
    },
    "AZTEC": {
        "english_name": "AZTEC",
        "persian_names": [],
    },
    "B": {
        "english_name": "B",
        "persian_names": [],
    },
    "B2": {
        "english_name": "B2",
        "persian_names": [],
    },
    "B3": {
        "english_name": "B3",
        "persian_names": [],
    },
    "BABY": {
        "english_name": "BABY",
        "persian_names": [],
    },
    "BABYDOGE": {
        "english_name": "BABYDOGE",
        "persian_names": ["بیبی دوچ"],
    },
    "BANANA": {
        "english_name": "BANANA",
        "persian_names": ["بنانا"],
    },
    "BANANAS31": {
        "english_name": "BANANAS31",
        "persian_names": [],
    },
    "BAND": {
        "english_name": "Band Protocol",
        "persian_names": ['بند پروتکل', 'بند'],
    },
    "BANK": {
        "english_name": "BANK",
        "persian_names": ["بانک"],
    },
    "BAR": {
        "english_name": "BAR",
        "persian_names": [],
    },
    "BARD": {
        "english_name": "BARD",
        "persian_names": [],
    },
    "BAS": {
        "english_name": "BAS",
        "persian_names": [],
    },
    "BASED": {
        "english_name": "BASED",
        "persian_names": [],
    },
    "BCH": {
        "english_name": "Bitcoin Cash",
        "persian_names": ["بیت‌کوین کش", "بیت کوین کش", "بیتکوین کش"],
    },
    "BDXN": {
        "english_name": "BDXN",
        "persian_names": [],
    },
    "BEAMX": {
        "english_name": "BEAMX",
        "persian_names": [],
    },
    "BEAT": {
        "english_name": "BEAT",
        "persian_names": [],
    },
    "BEL": {
        "english_name": "BEL",
        "persian_names": [],
    },
    "BELIEVE": {
        "english_name": "BELIEVE",
        "persian_names": [],
    },
    "BERA": {
        "english_name": "BERA",
        "persian_names": [],
    },
    "BICO": {
        "english_name": "BICO",
        "persian_names": [],
    },
    "BIGTIME": {
        "english_name": "BIGTIME",
        "persian_names": [],
    },
    "BILL": {
        "english_name": "BILL",
        "persian_names": [],
    },
    "BIO": {
        "english_name": "BIO",
        "persian_names": [],
    },
    "BIRB": {
        "english_name": "BIRB",
        "persian_names": [],
    },
    "BLEND": {
        "english_name": "BLEND",
        "persian_names": [],
    },
    "BLESS": {
        "english_name": "BLESS",
        "persian_names": [],
    },
    "BLUAI": {
        "english_name": "BLUAI",
        "persian_names": [],
    },
    "BLUR": {
        "english_name": "Blur",
        "persian_names": ['بلر'],
    },
    "BMT": {
        "english_name": "BMT",
        "persian_names": [],
    },
    "BNB": {
        "english_name": "BNB (Binance Coin)",
        "persian_names": ["بایننس کوین", "بی‌ان‌بی", "بی ان بی", "بایننس"],
    },
    "BNKR": {
        "english_name": "BNKR",
        "persian_names": [],
    },
    "BNT": {
        "english_name": "BNT",
        "persian_names": [],
    },
    "BOB": {
        "english_name": "BOB",
        "persian_names": [],
    },
    "BOME": {
        "english_name": "BOME",
        "persian_names": [],
    },
    "BONK": {
        "english_name": "BONK",
        "persian_names": [],
    },
    "BOOP": {
        "english_name": "BOOP",
        "persian_names": [],
    },
    "BOS": {
        "english_name": "BOS",
        "persian_names": [],
    },
    "BR": {
        "english_name": "BR",
        "persian_names": [],
    },
    "BREV": {
        "english_name": "BREV",
        "persian_names": [],
    },
    "BROCCOLI": {
        "english_name": "BROCCOLI",
        "persian_names": ["بروکلی"],
    },
    "BSB": {
        "english_name": "BSB",
        "persian_names": [],
    },
    "BTC": {
        "english_name": "Bitcoin",
        "persian_names": ["بیت‌کوین", "بیت کوین", "بیتکوین"],
    },
    "BTR": {
        "english_name": "BTR",
        "persian_names": [],
    },
    "BTW": {
        "english_name": "BTW",
        "persian_names": [],
    },
    "C": {
        "english_name": "C",
        "persian_names": [],
    },
    "CAKE": {
        "english_name": "CAKE",
        "persian_names": ["کیک"],
    },
    "CAMP": {
        "english_name": "CAMP",
        "persian_names": [],
    },
    "CARV": {
        "english_name": "CARV",
        "persian_names": [],
    },
    "CAT": {
        "english_name": "CAT",
        "persian_names": ["کت"],
    },
    "CATI": {
        "english_name": "CATI",
        "persian_names": [],
    },
    "CETUS": {
        "english_name": "CETUS",
        "persian_names": [],
    },
    "CFG": {
        "english_name": "CFG",
        "persian_names": [],
    },
    "CGN": {
        "english_name": "CGN",
        "persian_names": [],
    },
    "CGPT": {
        "english_name": "CGPT",
        "persian_names": [],
    },
    "CHIP": {
        "english_name": "CHIP",
        "persian_names": [],
    },
    "CHR": {
        "english_name": "CHR",
        "persian_names": [],
    },
    "CHZ": {
        "english_name": "Chiliz",
        "persian_names": ["چیلیز"],
    },
    "CITY": {
        "english_name": "CITY",
        "persian_names": ["سیتی"],
    },
    "CLANKER": {
        "english_name": "CLANKER",
        "persian_names": [],
    },
    "CLO": {
        "english_name": "CLO",
        "persian_names": [],
    },
    "COAI": {
        "english_name": "COAI",
        "persian_names": [],
    },
    "COINX": {
        "english_name": "COINX",
        "persian_names": [],
    },
    "COMMON": {
        "english_name": "COMMON",
        "persian_names": [],
    },
    "COMP": {
        "english_name": "Compound",
        "persian_names": ['کامپاند'],
    },
    "COOKIE": {
        "english_name": "COOKIE",
        "persian_names": ["کوکی"],
    },
    "COTI": {
        "english_name": "COTI",
        "persian_names": [],
    },
    "CRCLON": {
        "english_name": "CRCLON",
        "persian_names": [],
    },
    "CROSS": {
        "english_name": "CROSS",
        "persian_names": ["کراس"],
    },
    "CRV": {
        "english_name": "Curve DAO",
        "persian_names": ['کرو', 'کرو دائو'],
    },
    "CTK": {
        "english_name": "CTK",
        "persian_names": [],
    },
    "CTR": {
        "english_name": "CTR",
        "persian_names": [],
    },
    "CUDIS": {
        "english_name": "CUDIS",
        "persian_names": [],
    },
    "CYBER": {
        "english_name": "CYBER",
        "persian_names": ["سایبر"],
    },
    "DBR": {
        "english_name": "DBR",
        "persian_names": [],
    },
    "DEEP": {
        "english_name": "DEEP",
        "persian_names": ["دیپ"],
    },
    "DEOD": {
        "english_name": "DEOD",
        "persian_names": [],
    },
    "DFDVX": {
        "english_name": "DFDVX",
        "persian_names": [],
    },
    "DMC": {
        "english_name": "DMC",
        "persian_names": [],
    },
    "DN": {
        "english_name": "DN",
        "persian_names": [],
    },
    "DODO": {
        "english_name": "DODO",
        "persian_names": ["دودو"],
    },
    "DOGE": {
        "english_name": "Dogecoin",
        "persian_names": ["دوج‌کوین", "دوج", "دوج کوین", "دوجکوین"],
    },
    "DOGEGOV": {
        "english_name": "DOGEGOV",
        "persian_names": [],
    },
    "DOGINME": {
        "english_name": "DOGINME",
        "persian_names": [],
    },
    "DOGS": {
        "english_name": "DOGS",
        "persian_names": ["داگز"],
    },
    "DOLO": {
        "english_name": "DOLO",
        "persian_names": [],
    },
    "DOOD": {
        "english_name": "DOOD",
        "persian_names": [],
    },
    "DOT": {
        "english_name": "Polkadot",
        "persian_names": ["پولکادات", "دات"],
    },
    "DRIFT": {
        "english_name": "DRIFT",
        "persian_names": [],
    },
    "DUCK": {
        "english_name": "DUCK",
        "persian_names": ["داک"],
    },
    "DUSK": {
        "english_name": "DUSK",
        "persian_names": ["داسک"],
    },
    "DYDX": {
        "english_name": "dYdX",
        "persian_names": ['دی وای دی ایکس'],
    },
    "EDEN": {
        "english_name": "EDEN",
        "persian_names": [],
    },
    "EDGE": {
        "english_name": "EDGE",
        "persian_names": ["اج"],
    },
    "EDGEX": {
        "english_name": "EDGEX",
        "persian_names": [],
    },
    "EDU": {
        "english_name": "EDU",
        "persian_names": [],
    },
    "EGLD": {
        "english_name": "EGLD",
        "persian_names": [],
    },
    "EIGEN": {
        "english_name": "EIGEN",
        "persian_names": [],
    },
    "ELIZAOS": {
        "english_name": "ELIZAOS",
        "persian_names": [],
    },
    "ELSA": {
        "english_name": "ELSA",
        "persian_names": ["السا"],
    },
    "ENA": {
        "english_name": "Ethena",
        "persian_names": ["اتنا"],
    },
    "ENJ": {
        "english_name": "Enjin Coin",
        "persian_names": ['انجین کوین', 'انجین'],
    },
    "ENS": {
        "english_name": "Ethereum Name Service",
        "persian_names": ['اتریوم نیم سرویس', 'ای ان اس'],
    },
    "ENSO": {
        "english_name": "ENSO",
        "persian_names": [],
    },
    "EPIC": {
        "english_name": "EPIC",
        "persian_names": ["اپیک"],
    },
    "EPT": {
        "english_name": "EPT",
        "persian_names": [],
    },
    "ERA": {
        "english_name": "ERA",
        "persian_names": [],
    },
    "ES": {
        "english_name": "ES",
        "persian_names": [],
    },
    "ESP": {
        "english_name": "ESP",
        "persian_names": [],
    },
    "ESPORTS": {
        "english_name": "ESPORTS",
        "persian_names": [],
    },
    "ETC": {
        "english_name": "Ethereum Classic",
        "persian_names": ["اتریوم کلاسیک"],
    },
    "ETH": {
        "english_name": "Ethereum",
        "persian_names": ["اتریوم"],
    },
    "ETHFI": {
        "english_name": "ETHFI",
        "persian_names": [],
    },
    "ETHW": {
        "english_name": "ETHW",
        "persian_names": [],
    },
    "EUL": {
        "english_name": "EUL",
        "persian_names": [],
    },
    "EVAA": {
        "english_name": "EVAA",
        "persian_names": [],
    },
    "EWYB": {
        "english_name": "EWYB",
        "persian_names": [],
    },
    "F": {
        "english_name": "F",
        "persian_names": [],
    },
    "FARTCOIN": {
        "english_name": "Fartcoin",
        "persian_names": ["فارت‌کوین", "فارت کوین", "فارتکوین"],
    },
    "FDS": {
        "english_name": "FDS",
        "persian_names": [],
    },
    "FDUSD": {
        "english_name": "FDUSD",
        "persian_names": [],
    },
    "FET": {
        "english_name": "Fetch.ai",
        "persian_names": ['فتچ', 'فچ'],
    },
    "FF": {
        "english_name": "FF",
        "persian_names": [],
    },
    "FHE": {
        "english_name": "FHE",
        "persian_names": [],
    },
    "FIDA": {
        "english_name": "FIDA",
        "persian_names": [],
    },
    "FIGHT": {
        "english_name": "FIGHT",
        "persian_names": [],
    },
    "FIL": {
        "english_name": "Filecoin",
        "persian_names": ["فایل‌کوین", "فایل کوین", "فایلکوین"],
    },
    "FLOCK": {
        "english_name": "FLOCK",
        "persian_names": [],
    },
    "FLOKI": {
        "english_name": "Floki",
        "persian_names": ['فلوکی'],
    },
    "FLUID": {
        "english_name": "FLUID",
        "persian_names": [],
    },
    "FLUX": {
        "english_name": "FLUX",
        "persian_names": ["فلاکس"],
    },
    "FOLKS": {
        "english_name": "FOLKS",
        "persian_names": [],
    },
    "FORM": {
        "english_name": "FORM",
        "persian_names": ["فرم"],
    },
    "FRAG": {
        "english_name": "FRAG",
        "persian_names": ["فراگ"],
    },
    "FTT": {
        "english_name": "FTT",
        "persian_names": [],
    },
    "FWX": {
        "english_name": "FWX",
        "persian_names": [],
    },
    "G": {
        "english_name": "G",
        "persian_names": [],
    },
    "GAIA": {
        "english_name": "GAIA",
        "persian_names": [],
    },
    "GALA": {
        "english_name": "Gala",
        "persian_names": ['گالا'],
    },
    "GENIUS": {
        "english_name": "GENIUS",
        "persian_names": ["جینیوس"],
    },
    "GIGGLE": {
        "english_name": "GIGGLE",
        "persian_names": [],
    },
    "GLDX": {
        "english_name": "GLDX",
        "persian_names": [],
    },
    "GMT": {
        "english_name": "GMT",
        "persian_names": [],
    },
    "GMX": {
        "english_name": "GMX",
        "persian_names": [],
    },
    "GOAT": {
        "english_name": "GOAT",
        "persian_names": ["گوت"],
    },
    "GORK": {
        "english_name": "GORK",
        "persian_names": [],
    },
    "GPS": {
        "english_name": "GPS",
        "persian_names": ["جی پی اس"],
    },
    "GRASS": {
        "english_name": "GRASS",
        "persian_names": [],
    },
    "GRIFFAIN": {
        "english_name": "GRIFFAIN",
        "persian_names": [],
    },
    "GRT": {
        "english_name": "The Graph",
        "persian_names": ['گراف', 'د گراف'],
    },
    "GUA": {
        "english_name": "GUA",
        "persian_names": [],
    },
    "GWEI": {
        "english_name": "GWEI",
        "persian_names": [],
    },
    "H": {
        "english_name": "H",
        "persian_names": [],
    },
    "HAEDAL": {
        "english_name": "HAEDAL",
        "persian_names": [],
    },
    "HANA": {
        "english_name": "HANA",
        "persian_names": [],
    },
    "HBAR": {
        "english_name": "Hedera",
        "persian_names": ["هدرا"],
    },
    "HEI": {
        "english_name": "HEI",
        "persian_names": [],
    },
    "HEMI": {
        "english_name": "HEMI",
        "persian_names": [],
    },
    "HFT": {
        "english_name": "HFT",
        "persian_names": [],
    },
    "HIGH": {
        "english_name": "HIGH",
        "persian_names": [],
    },
    "HIPPO": {
        "english_name": "HIPPO",
        "persian_names": [],
    },
    "HMSTR": {
        "english_name": "HMSTR",
        "persian_names": ["همستر"],
    },
    "HNT": {
        "english_name": "HNT",
        "persian_names": [],
    },
    "HOLO": {
        "english_name": "HOLO",
        "persian_names": [],
    },
    "HOME": {
        "english_name": "HOME",
        "persian_names": ["هوم"],
    },
    "HOODX": {
        "english_name": "HOODX",
        "persian_names": [],
    },
    "HUMA": {
        "english_name": "HUMA",
        "persian_names": [],
    },
    "HYPE": {
        "english_name": "Hyperliquid",
        "persian_names": ["هایپرلیکویید", "هایپ"],
    },
    "HYPER": {
        "english_name": "HYPER",
        "persian_names": ["هایپر"],
    },
    "IAUON": {
        "english_name": "IAUON",
        "persian_names": [],
    },
    "ICNT": {
        "english_name": "ICNT",
        "persian_names": [],
    },
    "ICP": {
        "english_name": "Internet Computer",
        "persian_names": ["اینترن‌ت کامپیوتر", "اینترنت کامپیوتِر"],
    },
    "ID": {
        "english_name": "ID",
        "persian_names": [],
    },
    "IDOL": {
        "english_name": "IDOL",
        "persian_names": [],
    },
    "IKA": {
        "english_name": "IKA",
        "persian_names": [],
    },
    "ILV": {
        "english_name": "ILV",
        "persian_names": [],
    },
    "IMX": {
        "english_name": "Immutable",
        "persian_names": ['ایمیوتبل'],
    },
    "IN": {
        "english_name": "IN",
        "persian_names": [],
    },
    "INJ": {
        "english_name": "Injective",
        "persian_names": ['اینجکتیو'],
    },
    "INTCB": {
        "english_name": "INTCB",
        "persian_names": [],
    },
    "INX": {
        "english_name": "INX",
        "persian_names": [],
    },
    "IO": {
        "english_name": "IO",
        "persian_names": [],
    },
    "IR": {
        "english_name": "IR",
        "persian_names": [],
    },
    "IRYS": {
        "english_name": "IRYS",
        "persian_names": [],
    },
    "ITE": {
        "english_name": "ITE",
        "persian_names": [],
    },
    "J": {
        "english_name": "J",
        "persian_names": [],
    },
    "JASMY": {
        "english_name": "JasmyCoin",
        "persian_names": ['جسمی'],
    },
    "JCT": {
        "english_name": "JCT",
        "persian_names": [],
    },
    "JELLYJELLY": {
        "english_name": "JELLYJELLY",
        "persian_names": [],
    },
    "JST": {
        "english_name": "JST",
        "persian_names": [],
    },
    "JTO": {
        "english_name": "JTO",
        "persian_names": [],
    },
    "JUP": {
        "english_name": "Jupiter",
        "persian_names": ['ژوپیتر'],
    },
    "JUV": {
        "english_name": "JUV",
        "persian_names": [],
    },
    "KAIO": {
        "english_name": "KAIO",
        "persian_names": [],
    },
    "KAITO": {
        "english_name": "KAITO",
        "persian_names": [],
    },
    "KERNEL": {
        "english_name": "KERNEL",
        "persian_names": ["کرنل"],
    },
    "KGEN": {
        "english_name": "KGEN",
        "persian_names": [],
    },
    "KILO": {
        "english_name": "KILO",
        "persian_names": ["کیلو"],
    },
    "KITE": {
        "english_name": "KITE",
        "persian_names": ["کایت"],
    },
    "KLINK": {
        "english_name": "KLINK",
        "persian_names": [],
    },
    "KMNO": {
        "english_name": "KMNO",
        "persian_names": [],
    },
    "LA": {
        "english_name": "LA",
        "persian_names": [],
    },
    "LAB": {
        "english_name": "LAB",
        "persian_names": [],
    },
    "LAVA": {
        "english_name": "LAVA",
        "persian_names": ["لاوا"],
    },
    "LAYER": {
        "english_name": "LAYER",
        "persian_names": ["لایر"],
    },
    "LAZIO": {
        "english_name": "LAZIO",
        "persian_names": [],
    },
    "LDO": {
        "english_name": "Lido DAO",
        "persian_names": ['لیدو', 'لیدو دائو'],
    },
    "LIGHT": {
        "english_name": "LIGHT",
        "persian_names": ["لایت"],
    },
    "LINEA": {
        "english_name": "LINEA",
        "persian_names": [],
    },
    "LINK": {
        "english_name": "Chainlink",
        "persian_names": ["چین‌لینک", "لینک", "چین لینک", "چینلینک"],
    },
    "LISTA": {
        "english_name": "LISTA",
        "persian_names": [],
    },
    "LIT2": {
        "english_name": "LIT2",
        "persian_names": [],
    },
    "LITKEY": {
        "english_name": "LITKEY",
        "persian_names": [],
    },
    "LPT": {
        "english_name": "LPT",
        "persian_names": [],
    },
    "LQTY": {
        "english_name": "LQTY",
        "persian_names": [],
    },
    "LRC": {
        "english_name": "LRC",
        "persian_names": [],
    },
    "LTC": {
        "english_name": "Litecoin",
        "persian_names": ["لایت‌کوین", "لایت کوین", "لایتکوین"],
    },
    "LYN": {
        "english_name": "LYN",
        "persian_names": [],
    },
    "MAGIC": {
        "english_name": "MAGIC",
        "persian_names": ["مجیک"],
    },
    "MAGMA": {
        "english_name": "MAGMA",
        "persian_names": ["ماگما"],
    },
    "MAJOR": {
        "english_name": "MAJOR",
        "persian_names": ["مجر", "میجور"],
    },
    "MANA": {
        "english_name": "Decentraland",
        "persian_names": ['دیسنترالند', 'مانا'],
    },
    "MANTA": {
        "english_name": "MANTA",
        "persian_names": [],
    },
    "MASK": {
        "english_name": "MASK",
        "persian_names": ["ماسک"],
    },
    "MAV": {
        "english_name": "MAV",
        "persian_names": [],
    },
    "MAVIA": {
        "english_name": "MAVIA",
        "persian_names": [],
    },
    "MBG": {
        "english_name": "MBG",
        "persian_names": [],
    },
    "MBOX": {
        "english_name": "MBOX",
        "persian_names": [],
    },
    "MCDX": {
        "english_name": "MCDX",
        "persian_names": [],
    },
    "ME": {
        "english_name": "ME",
        "persian_names": [],
    },
    "MELANIA": {
        "english_name": "MELANIA",
        "persian_names": [],
    },
    "MEME": {
        "english_name": "MEME",
        "persian_names": ["میم"],
    },
    "MET": {
        "english_name": "MET",
        "persian_names": [],
    },
    "METAX": {
        "english_name": "METAX",
        "persian_names": [],
    },
    "METIS": {
        "english_name": "METIS",
        "persian_names": [],
    },
    "MEW": {
        "english_name": "MEW",
        "persian_names": [],
    },
    "MIRA": {
        "english_name": "MIRA",
        "persian_names": [],
    },
    "MITO": {
        "english_name": "MITO",
        "persian_names": [],
    },
    "MMT": {
        "english_name": "MMT",
        "persian_names": [],
    },
    "MOODENG": {
        "english_name": "MOODENG",
        "persian_names": [],
    },
    "MORPHO": {
        "english_name": "MORPHO",
        "persian_names": [],
    },
    "MOVE": {
        "english_name": "MOVE",
        "persian_names": [],
    },
    "MPLX": {
        "english_name": "MPLX",
        "persian_names": [],
    },
    "MSTRON": {
        "english_name": "MSTRON",
        "persian_names": [],
    },
    "MUBARAK": {
        "english_name": "MUBARAK",
        "persian_names": [],
    },
    "NAORIS": {
        "english_name": "NAORIS",
        "persian_names": [],
    },
    "NC": {
        "english_name": "NC",
        "persian_names": [],
    },
    "NEAR": {
        "english_name": "NEAR Protocol",
        "persian_names": ["نیر", "نئیر"],
    },
    "NEIRO1": {
        "english_name": "NEIRO1",
        "persian_names": [],
    },
    "NES": {
        "english_name": "NES",
        "persian_names": [],
    },
    "NEWT": {
        "english_name": "NEWT",
        "persian_names": [],
    },
    "NIGHT": {
        "english_name": "NIGHT",
        "persian_names": [],
    },
    "NOM": {
        "english_name": "NOM",
        "persian_names": [],
    },
    "NOT": {
        "english_name": "NOT",
        "persian_names": [],
    },
    "NS": {
        "english_name": "NS",
        "persian_names": [],
    },
    "NUMI": {
        "english_name": "NUMI",
        "persian_names": [],
    },
    "NVDAON": {
        "english_name": "NVDAON",
        "persian_names": [],
    },
    "NXPC": {
        "english_name": "NXPC",
        "persian_names": [],
    },
    "NXQ": {
        "english_name": "NXQ",
        "persian_names": [],
    },
    "O1": {
        "english_name": "O1",
        "persian_names": [],
    },
    "OBOL": {
        "english_name": "OBOL",
        "persian_names": [],
    },
    "OFC": {
        "english_name": "OFC",
        "persian_names": [],
    },
    "OG": {
        "english_name": "OG",
        "persian_names": [],
    },
    "OGN": {
        "english_name": "OGN",
        "persian_names": [],
    },
    "ON": {
        "english_name": "ON",
        "persian_names": [],
    },
    "ONDO": {
        "english_name": "Ondo Finance",
        "persian_names": ["اوندو"],
    },
    "ONE": {
        "english_name": "ONE",
        "persian_names": ["وان"],
    },
    "OP": {
        "english_name": "OP",
        "persian_names": [],
    },
    "OPEN": {
        "english_name": "OPEN",
        "persian_names": ["اپن"],
    },
    "OPG": {
        "english_name": "OPG",
        "persian_names": [],
    },
    "OPN": {
        "english_name": "OPN",
        "persian_names": [],
    },
    "ORCA": {
        "english_name": "ORCA",
        "persian_names": [],
    },
    "ORDI": {
        "english_name": "ORDI",
        "persian_names": [],
    },
    "OWL": {
        "english_name": "OWL",
        "persian_names": [],
    },
    "P": {
        "english_name": "P",
        "persian_names": [],
    },
    "PARTI": {
        "english_name": "PARTI",
        "persian_names": [],
    },
    "PAXG": {
        "english_name": "PAXG",
        "persian_names": ["پکس گلد", "پکسگلد"],
    },
    "PENDLE": {
        "english_name": "PENDLE",
        "persian_names": [],
    },
    "PENGU": {
        "english_name": "PENGU",
        "persian_names": [],
    },
    "PENGUIN": {
        "english_name": "PENGUIN",
        "persian_names": [],
    },
    "PEOPLE": {
        "english_name": "PEOPLE",
        "persian_names": [],
    },
    "PEPE": {
        "english_name": "Pepe",
        "persian_names": ["پپه", "پپه کوین", "پپه‌کوین", "په په"],
    },
    "PHA": {
        "english_name": "PHA",
        "persian_names": [],
    },
    "PIEVERSE": {
        "english_name": "PIEVERSE",
        "persian_names": [],
    },
    "PIPPIN": {
        "english_name": "PIPPIN",
        "persian_names": [],
    },
    "PIXEL": {
        "english_name": "PIXEL",
        "persian_names": ["پیکسل"],
    },
    "PLAY": {
        "english_name": "PLAY",
        "persian_names": ["پلی"],
    },
    "PLC": {
        "english_name": "PLC",
        "persian_names": [],
    },
    "PLUME": {
        "english_name": "PLUME",
        "persian_names": [],
    },
    "PNUT": {
        "english_name": "PNUT",
        "persian_names": [],
    },
    "POL": {
        "english_name": "Polygon Ecosystem Token",
        "persian_names": ["پالیگان", "پول"],
    },
    "POPCAT": {
        "english_name": "POPCAT",
        "persian_names": ["پاپ‌کت", "پاپ کت"],
    },
    "PORTALS": {
        "english_name": "PORTALS",
        "persian_names": [],
    },
    "PORTO": {
        "english_name": "PORTO",
        "persian_names": [],
    },
    "POWER": {
        "english_name": "POWER",
        "persian_names": ["پاور"],
    },
    "PRL": {
        "english_name": "PRL",
        "persian_names": [],
    },
    "PROMPT": {
        "english_name": "PROMPT",
        "persian_names": ["پرامپت"],
    },
    "PROVE": {
        "english_name": "PROVE",
        "persian_names": [],
    },
    "PSG": {
        "english_name": "PSG",
        "persian_names": ["پی‌اس‌جی", "پی اس جی"],
    },
    "PTB": {
        "english_name": "PTB",
        "persian_names": [],
    },
    "PUBLIC": {
        "english_name": "PUBLIC",
        "persian_names": ["پابلیک"],
    },
    "PUMP": {
        "english_name": "PUMP",
        "persian_names": ["پامپ"],
    },
    "PUMP2": {
        "english_name": "PUMP2",
        "persian_names": [],
    },
    "PUNCHI": {
        "english_name": "PUNCHI",
        "persian_names": ["پانچی"],
    },
    "PUNDIXNEW": {
        "english_name": "PUNDIXNEW",
        "persian_names": [],
    },
    "PYBOBO": {
        "english_name": "PYBOBO",
        "persian_names": [],
    },
    "PYR": {
        "english_name": "PYR",
        "persian_names": [],
    },
    "PYTH": {
        "english_name": "Pyth Network",
        "persian_names": ['پایت', 'پایت نتورک'],
    },
    "Q": {
        "english_name": "Q",
        "persian_names": ["کیو"],
    },
    "QAIT": {
        "english_name": "QAIT",
        "persian_names": [],
    },
    "QKC": {
        "english_name": "QKC",
        "persian_names": [],
    },
    "QQQX": {
        "english_name": "QQQX",
        "persian_names": [],
    },
    "RAD": {
        "english_name": "RAD",
        "persian_names": [],
    },
    "RARE": {
        "english_name": "RARE",
        "persian_names": [],
    },
    "RATS": {
        "english_name": "RATS",
        "persian_names": [],
    },
    "RAVE": {
        "english_name": "RAVE",
        "persian_names": [],
    },
    "RAY": {
        "english_name": "RAY",
        "persian_names": [],
    },
    "RE": {
        "english_name": "RE",
        "persian_names": [],
    },
    "RECALL": {
        "english_name": "RECALL",
        "persian_names": [],
    },
    "RED": {
        "english_name": "RED",
        "persian_names": [],
    },
    "RENDER": {
        "english_name": "Render",
        "persian_names": ['رندر'],
    },
    "RESOLV": {
        "english_name": "RESOLV",
        "persian_names": [],
    },
    "REZ": {
        "english_name": "REZ",
        "persian_names": [],
    },
    "RHEA": {
        "english_name": "RHEA",
        "persian_names": [],
    },
    "RION": {
        "english_name": "RION",
        "persian_names": [],
    },
    "RIVER": {
        "english_name": "RIVER",
        "persian_names": [],
    },
    "RLS": {
        "english_name": "RLS",
        "persian_names": [],
    },
    "ROBO": {
        "english_name": "ROBO",
        "persian_names": [],
    },
    "ROLL": {
        "english_name": "ROLL",
        "persian_names": [],
    },
    "RSR": {
        "english_name": "RSR",
        "persian_names": [],
    },
    "RWA": {
        "english_name": "RWA",
        "persian_names": [],
    },
    "S": {
        "english_name": "S",
        "persian_names": [],
    },
    "SAHARA": {
        "english_name": "SAHARA",
        "persian_names": [],
    },
    "SAND": {
        "english_name": "The Sandbox",
        "persian_names": ['سندباکس'],
    },
    "SANTOS": {
        "english_name": "SANTOS",
        "persian_names": [],
    },
    "SAPIEN": {
        "english_name": "SAPIEN",
        "persian_names": [],
    },
    "SAROS": {
        "english_name": "SAROS",
        "persian_names": [],
    },
    "SATS": {
        "english_name": "SATS",
        "persian_names": [],
    },
    "SENT": {
        "english_name": "SENT",
        "persian_names": [],
    },
    "SFP": {
        "english_name": "SFP",
        "persian_names": [],
    },
    "SHELL": {
        "english_name": "SHELL",
        "persian_names": ["شل"],
    },
    "SHIB": {
        "english_name": "Shiba Inu",
        "persian_names": ["شیبا", "شیبا اینو"],
    },
    "SHOW": {
        "english_name": "SHOW",
        "persian_names": [],
    },
    "SIGN": {
        "english_name": "SIGN",
        "persian_names": [],
    },
    "SIREN": {
        "english_name": "SIREN",
        "persian_names": [],
    },
    "SKR": {
        "english_name": "SKR",
        "persian_names": [],
    },
    "SKY": {
        "english_name": "SKY",
        "persian_names": [],
    },
    "SKYAI": {
        "english_name": "SKYAI",
        "persian_names": [],
    },
    "SLVON": {
        "english_name": "SLVON",
        "persian_names": [],
    },
    "SOL": {
        "english_name": "Solana",
        "persian_names": ["سولانا"],
    },
    "SOLIB": {
        "english_name": "SOLIB",
        "persian_names": [],
    },
    "SOLSTICE": {
        "english_name": "SOLSTICE",
        "persian_names": [],
    },
    "SOLV": {
        "english_name": "SOLV",
        "persian_names": [],
    },
    "SOMI": {
        "english_name": "SOMI",
        "persian_names": [],
    },
    "SONIC24": {
        "english_name": "SONIC24",
        "persian_names": [],
    },
    "SOON": {
        "english_name": "SOON",
        "persian_names": [],
    },
    "SOSO": {
        "english_name": "SOSO",
        "persian_names": [],
    },
    "SPACE": {
        "english_name": "SPACE",
        "persian_names": [],
    },
    "SPCXX": {
        "english_name": "SPCXX",
        "persian_names": ["اسپیس ایکس", "اسپیس‌ایکس", "اسپیس اکس"],
    },
    "SPK": {
        "english_name": "SPK",
        "persian_names": [],
    },
    "SPON": {
        "english_name": "SPON",
        "persian_names": [],
    },
    "SPORTFUN": {
        "english_name": "SPORTFUN",
        "persian_names": [],
    },
    "SPURS": {
        "english_name": "SPURS",
        "persian_names": [],
    },
    "SQD": {
        "english_name": "SQD",
        "persian_names": [],
    },
    "SSV": {
        "english_name": "SSV",
        "persian_names": [],
    },
    "ST": {
        "english_name": "ST",
        "persian_names": [],
    },
    "STBL": {
        "english_name": "STBL",
        "persian_names": [],
    },
    "STG": {
        "english_name": "STG",
        "persian_names": [],
    },
    "STO": {
        "english_name": "STO",
        "persian_names": [],
    },
    "STORJ": {
        "english_name": "Storj",
        "persian_names": ['استورج'],
    },
    "STRK": {
        "english_name": "Starknet",
        "persian_names": ['استارک نت'],
    },
    "SUI": {
        "english_name": "Sui",
        "persian_names": ["سویی"],
    },
    "SUPER": {
        "english_name": "SUPER",
        "persian_names": ["سوپر"],
    },
    "SUSHI": {
        "english_name": "SushiSwap",
        "persian_names": ['سوشی', 'سوشی سواپ'],
    },
    "SWARMS": {
        "english_name": "SWARMS",
        "persian_names": [],
    },
    "SXT": {
        "english_name": "SXT",
        "persian_names": [],
    },
    "SYN": {
        "english_name": "SYN",
        "persian_names": [],
    },
    "SYRUP": {
        "english_name": "SYRUP",
        "persian_names": [],
    },
    "TA": {
        "english_name": "TA",
        "persian_names": [],
    },
    "TAC": {
        "english_name": "TAC",
        "persian_names": [],
    },
    "TAG": {
        "english_name": "TAG",
        "persian_names": ["تگ"],
    },
    "TAIKO": {
        "english_name": "Taiko",
        "persian_names": ['تایکو'],
    },
    "TAKE": {
        "english_name": "TAKE",
        "persian_names": [],
    },
    "TANSSI": {
        "english_name": "TANSSI",
        "persian_names": [],
    },
    "TCOM": {
        "english_name": "TCOM",
        "persian_names": [],
    },
    "THE": {
        "english_name": "THE",
        "persian_names": [],
    },
    "THQ": {
        "english_name": "THQ",
        "persian_names": [],
    },
    "TLM": {
        "english_name": "Alien Worlds",
        "persian_names": ['الین ورلدز'],
    },
    "TNSR": {
        "english_name": "TNSR",
        "persian_names": [],
    },
    "TOKEN": {
        "english_name": "TOKEN",
        "persian_names": ["توکن"],
    },
    "TOSHI": {
        "english_name": "TOSHI",
        "persian_names": ["توشی"],
    },
    "TOWNS": {
        "english_name": "TOWNS",
        "persian_names": [],
    },
    "TRAC": {
        "english_name": "TRAC",
        "persian_names": [],
    },
    "TRADOOR": {
        "english_name": "TRADOOR",
        "persian_names": [],
    },
    "TRB": {
        "english_name": "TRB",
        "persian_names": [],
    },
    "TREE": {
        "english_name": "TREE",
        "persian_names": [],
    },
    "TRIA": {
        "english_name": "TRIA",
        "persian_names": [],
    },
    "TRUMP": {
        "english_name": "Official Trump",
        "persian_names": ["ترامپ", "توکن ترامپ"],
    },
    "TRUST": {
        "english_name": "TRUST",
        "persian_names": ["تراست"],
    },
    "TRUTH": {
        "english_name": "TRUTH",
        "persian_names": [],
    },
    "TRX": {
        "english_name": "TRON",
        "persian_names": ["ترون"],
    },
    "TSLAON": {
        "english_name": "TSLAON",
        "persian_names": [],
    },
    "TST": {
        "english_name": "TST",
        "persian_names": [],
    },
    "TURBO": {
        "english_name": "TURBO",
        "persian_names": ["توربو"],
    },
    "TURTLE": {
        "english_name": "TURTLE",
        "persian_names": [],
    },
    "TUT": {
        "english_name": "TUT",
        "persian_names": [],
    },
    "TWT": {
        "english_name": "Trust Wallet Token",
        "persian_names": ['تراست ولت'],
    },
    "U": {
        "english_name": "U",
        "persian_names": [],
    },
    "UAI": {
        "english_name": "UAI",
        "persian_names": [],
    },
    "UB": {
        "english_name": "UB",
        "persian_names": [],
    },
    "UNI": {
        "english_name": "Uniswap",
        "persian_names": ["یونی‌سواپ", "یونی", "یونی سواپ", "یونیسواپ"],
    },
    "UP": {
        "english_name": "UP",
        "persian_names": ["آپ"],
    },
    "US": {
        "english_name": "US",
        "persian_names": [],
    },
    "USD1": {
        "english_name": "USD1",
        "persian_names": [],
    },
    "USDC": {
        "english_name": "USDC",
        "persian_names": [],
    },
    "USDE": {
        "english_name": "USDE",
        "persian_names": [],
    },
    "USDS": {
        "english_name": "USDS",
        "persian_names": [],
    },
    "USELESS": {
        "english_name": "USELESS",
        "persian_names": [],
    },
    "USUAL": {
        "english_name": "USUAL",
        "persian_names": [],
    },
    "VELODROME": {
        "english_name": "VELODROME",
        "persian_names": [],
    },
    "VELVET": {
        "english_name": "VELVET",
        "persian_names": [],
    },
    "VFY": {
        "english_name": "VFY",
        "persian_names": [],
    },
    "VINE": {
        "english_name": "VINE",
        "persian_names": [],
    },
    "VIRTUAL": {
        "english_name": "VIRTUAL",
        "persian_names": [],
    },
    "VOOI": {
        "english_name": "VOOI",
        "persian_names": [],
    },
    "VSN": {
        "english_name": "VSN",
        "persian_names": [],
    },
    "VVV": {
        "english_name": "VVV",
        "persian_names": [],
    },
    "W": {
        "english_name": "W",
        "persian_names": [],
    },
    "WAL": {
        "english_name": "WAL",
        "persian_names": [],
    },
    "WARD": {
        "english_name": "WARD",
        "persian_names": [],
    },
    "WAVES": {
        "english_name": "WAVES",
        "persian_names": [],
    },
    "WCT": {
        "english_name": "WCT",
        "persian_names": [],
    },
    "WET": {
        "english_name": "WET",
        "persian_names": [],
    },
    "WHITEWHALE": {
        "english_name": "WHITEWHALE",
        "persian_names": [],
    },
    "WIF": {
        "english_name": "WIF",
        "persian_names": [],
    },
    "WIN": {
        "english_name": "WIN",
        "persian_names": [],
    },
    "WLD": {
        "english_name": "Worldcoin",
        "persian_names": ['ورلد کوین'],
    },
    "WLFI": {
        "english_name": "WLFI",
        "persian_names": [],
    },
    "WOD": {
        "english_name": "WOD",
        "persian_names": [],
    },
    "WOO": {
        "english_name": "WOO",
        "persian_names": [],
    },
    "XAN": {
        "english_name": "XAN",
        "persian_names": [],
    },
    "XAUT": {
        "english_name": "XAUT",
        "persian_names": [],
    },
    "XCN": {
        "english_name": "XCN",
        "persian_names": [],
    },
    "XCX": {
        "english_name": "XCX",
        "persian_names": [],
    },
    "XLM": {
        "english_name": "Stellar",
        "persian_names": ["استلار"],
    },
    "XNY": {
        "english_name": "XNY",
        "persian_names": [],
    },
    "XPIN": {
        "english_name": "XPIN",
        "persian_names": [],
    },
    "XPL": {
        "english_name": "XPL",
        "persian_names": [],
    },
    "XRP": {
        "english_name": "XRP (Ripple)",
        "persian_names": ["ریپل", "ایکس‌آرپی", "ایکس آر پی"],
    },
    "XTZ": {
        "english_name": "Tezos",
        "persian_names": ['تزوس'],
    },
    "XVS": {
        "english_name": "XVS",
        "persian_names": [],
    },
    "YB": {
        "english_name": "YB",
        "persian_names": [],
    },
    "YGG": {
        "english_name": "YGG",
        "persian_names": [],
    },
    "ZAMA": {
        "english_name": "ZAMA",
        "persian_names": [],
    },
    "ZBCN": {
        "english_name": "ZBCN",
        "persian_names": [],
    },
    "ZBT": {
        "english_name": "ZBT",
        "persian_names": [],
    },
    "ZEC": {
        "english_name": "Zcash",
        "persian_names": ['زدکش', 'زی‌کش', 'زی کش'],
    },
    "ZENT": {
        "english_name": "ZENT",
        "persian_names": [],
    },
    "ZEREBRO": {
        "english_name": "ZEREBRO",
        "persian_names": [],
    },
    "ZEST": {
        "english_name": "ZEST",
        "persian_names": [],
    },
    "ZETA": {
        "english_name": "ZETA",
        "persian_names": [],
    },
    "ZEUS": {
        "english_name": "ZEUS",
        "persian_names": ['زئوس', 'زیوس'],
    },
    "ZKC": {
        "english_name": "ZKC",
        "persian_names": [],
    },
    "ZKP": {
        "english_name": "ZKP",
        "persian_names": [],
    },
    "ZKWASM": {
        "english_name": "ZKWASM",
        "persian_names": [],
    },
    "ZORA": {
        "english_name": "ZORA",
        "persian_names": [],
    },
    "ZRC": {
        "english_name": "ZRC",
        "persian_names": [],
    },
    "ZRO": {
        "english_name": "LayerZero",
        "persian_names": ['لیر زیرو'],
    },
}

# =============================================================================
# INTERNAL LOOKUP TABLES (built from CRYPTO_SYMBOLS)
# =============================================================================

# Build a reverse lookup: name -> symbol (lowercased for case-insensitive matching)
_SYMBOL_LOOKUP = {}

for __symbol, __info in CRYPTO_SYMBOLS.items():
    # Map the ticker symbol itself (uppercase)
    _SYMBOL_LOOKUP[__symbol.upper()] = __symbol

    # Map the English name (lowercased)
    if __info.get("english_name"):
        _SYMBOL_LOOKUP[__info["english_name"].lower()] = __symbol

    # Map Persian names (as-is, no lowercasing needed for Persian)
    for __pname in __info.get("persian_names", []):
        _SYMBOL_LOOKUP[__pname] = __symbol
        _SYMBOL_LOOKUP[__pname.lower()] = __symbol
        # Also map without half-spaces (ZWNJ) for easier matching
        _SYMBOL_LOOKUP[__pname.replace("\u200c", "").lower()] = __symbol
        _SYMBOL_LOOKUP[__pname.replace("\u200c", "")] = __symbol

# Build a sorted list of all resolvable aliases for substring matching.
# Sorted by length descending so that longer/more-specific names are matched first.
_RESOLVABLE_ALIASES = []
_seen_aliases = set()

for __symbol, __info in CRYPTO_SYMBOLS.items():
    # Ticker symbol
    for __alias in (__symbol, __symbol.upper()):
        if __alias and __alias not in _seen_aliases:
            _seen_aliases.add(__alias)
            _RESOLVABLE_ALIASES.append((__alias, __symbol))

    # English name
    __eng = __info.get("english_name", "")
    if __eng:
        for __alias in (__eng, __eng.lower()):
            if __alias and __alias not in _seen_aliases:
                _seen_aliases.add(__alias)
                _RESOLVABLE_ALIASES.append((__alias, __symbol))

    # Persian names and their normalized variants
    for __pname in __info.get("persian_names", []):
        for __alias in (
            __pname,
            __pname.lower(),
            __pname.replace("\u200c", ""),
            __pname.replace("\u200c", "").lower(),
        ):
            if __alias and __alias not in _seen_aliases:
                _seen_aliases.add(__alias)
                _RESOLVABLE_ALIASES.append((__alias, __symbol))

_RESOLVABLE_ALIASES.sort(key=lambda x: len(x[0]), reverse=True)


def resolve_symbol(input_text: str) -> str | None:
    """
    Resolve user input to a crypto ticker symbol.

    Checks in order:
    1. Direct symbol match (e.g., "BTC" -> "BTC")
    2. English name match (e.g., "Bitcoin" -> "BTC")
    3. Persian name match (e.g., "بیت‌کوین" -> "BTC")
    4. Normalized Persian name (e.g., "بیتکوین" -> "BTC")

    Args:
        input_text: The user's input (can be symbol, English name, or Persian name)

    Returns:
        The ticker symbol (e.g., "BTC") if found, None otherwise.
    """
    if not input_text or not isinstance(input_text, str):
        return None

    text = input_text.strip()

    # Direct lookup (case-insensitive for English)
    # First try exact symbol match (uppercase)
    if text.upper() in _SYMBOL_LOOKUP:
        result = _SYMBOL_LOOKUP[text.upper()]
        return result

    # Then try exact Persian name match
    if text in _SYMBOL_LOOKUP:
        result = _SYMBOL_LOOKUP[text]
        return result

    # Then try lowercase match
    text_lower = text.lower()
    if text_lower in _SYMBOL_LOOKUP:
        result = _SYMBOL_LOOKUP[text_lower]
        return result

    # Try normalized Persian (remove half-spaces)
    text_normalized = text.replace("\u200c", "")
    if text_normalized in _SYMBOL_LOOKUP:
        result = _SYMBOL_LOOKUP[text_normalized]
        return result
    if text_normalized.lower() in _SYMBOL_LOOKUP:
        result = _SYMBOL_LOOKUP[text_normalized]
        return result

    return None


def resolve_symbol_contained(input_text: str) -> str | None:
    """
    Resolve a crypto ticker symbol from free-form user text.

    First tries an exact match (same as ``resolve_symbol``). If that fails, it
    looks for any known English/Persian name or ticker symbol contained as a
    whole word/phrase within ``input_text``.

    Examples:
        "give me eth"          -> "ETH"
        "تحلیل اتریوم"          -> "ETH"
        "what about Bitcoin?"  -> "BTC"
        "خبرهای دوج کوین"       -> "DOGE"
        "invalid text"         -> None

    Args:
        input_text: Free-form text possibly containing a known crypto name.

    Returns:
        The ticker symbol if a known name/symbol is found, None otherwise.
    """
    if not input_text or not isinstance(input_text, str):
        return None

    text = input_text.strip()
    if not text:
        return None

    # 1. Exact direct matches first.
    direct = resolve_symbol(text)
    if direct:
        return direct

    # 2. Substring search with word boundaries.
    # Longer aliases are tried first to prefer specific names over short
    # ticker symbols (e.g. "Bitcoin Cash" before "Bitcoin").
    for alias, symbol in _RESOLVABLE_ALIASES:
        if len(alias) < 2:
            continue
        # Case-insensitive for ASCII aliases only (tickers and English names).
        flags = re.IGNORECASE if alias.isascii() else 0
        pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
        if re.search(pattern, text, flags=flags):
            return symbol

    return None


NEWS_VALID_SYMBOLS = [
    "BTC", "ADA", "ETH", "DOGE", "BNB", "XRP", "SOL", "TON", "TRX", "LTC",
    "DOT", "AVAX", "LINK", "MATIC", "POL", "SUI", "LEO", "SHIB", "HBAR", "XLM",
    "BCH", "HYPE", "BGB", "XMR", "PI", "PEPE", "UNI", "APT", "OKB", "ONDO",
    "NEAR", "TRUMP", "TAO", "ICP", "KAS", "ETC", "AAVE", "MNT", "ENA", "FIL",
    "FARTCOIN",
]


def get_valid_symbols() -> list[str]:
    """Get list of all valid ticker symbols (for chart analysis)."""
    return list(CRYPTO_SYMBOLS.keys())


def get_news_valid_symbols() -> list[str]:
    """Get list of valid ticker symbols for news analysis."""
    return NEWS_VALID_SYMBOLS


def get_symbol_info(symbol: str) -> dict | None:
    """Get info for a specific symbol."""
    return CRYPTO_SYMBOLS.get(symbol.upper())


def is_valid_symbol(input_text: str) -> bool:
    """Check if input is a valid symbol or name that can be resolved."""
    return resolve_symbol(input_text) is not None
