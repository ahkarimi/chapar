"""Small, dependency-free localization helpers for the Telegram bot."""

SUPPORTED_LANGUAGES = {"en", "fa"}
DEFAULT_LANGUAGE = "fa"


def normalize_language(language: str | None) -> str:
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def text(language: str | None, english: str, persian: str) -> str:
    return english if normalize_language(language) == "en" else persian


BUTTONS = {
    "chart": {"en": "📊 Chart analysis", "fa": "📊 تحلیل چارت"},
    "chat": {"en": "💬 Chat with AI", "fa": "💬 چت با AI"},
    "news": {"en": "📰 News analysis (free)", "fa": "📰 تحلیل اخبار (رایگان)"},
    "subscription": {"en": "⭐️ Monthly subscription", "fa": "⭐️ اشتراک ماهانه"},
    "market": {"en": "💰 Gold & USD", "fa": "💰 طلا و دلار"},
    "profile": {"en": "👤 My profile", "fa": "👤 پروفایل من"},
    "admin": {"en": "👮 Admin panel", "fa": "👮 پنل مدیریت"},
    "back": {"en": "• Back •", "fa": "• برگشت •"},
    "clear_chat": {"en": "🗑 Clear chat history", "fa": "🗑 پاک کردن تاریخچه چت"},
    "usd_price": {"en": "• USD price •", "fa": "• قیمت دلار •"},
    "gold_price": {"en": "• Gold price •", "fa": "• قیمت طلا •"},
    "education": {"en": "• Exchange & trading guide •", "fa": "• آموزش صرافی و ترید •"},
    "prize": {"en": "• Prize •", "fa": "• جایزه •"},
    "language": {"en": "🌐 Language", "fa": "🌐 زبان"},
}


def button(key: str, language: str | None) -> str:
    return BUTTONS[key][normalize_language(language)]


def is_button(value: str, key: str) -> bool:
    return value in BUTTONS[key].values()

