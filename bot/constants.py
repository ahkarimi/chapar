import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def _safe_int_env(name, default=0):
    """Safely get an integer environment variable, returning default if missing or empty."""
    val = os.getenv(name, "")
    if val == "":
        return default
    return int(val)


def _positive_int_list_env(name):
    values = []
    for raw_value in os.getenv(name, "").split(","):
        raw_value = raw_value.strip()
        if raw_value:
            value = int(raw_value)
            if value > 0 and value not in values:
                values.append(value)
    return tuple(values)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_DEBUG = os.getenv("BOT_DEBUG", "false").lower() == "true"
BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "fa")

# Admin configuration
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else []
ADMINS = ADMIN_IDS  # Alias for backward compatibility


# PostgreSQL configuration

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_DEBUG = os.getenv("BOT_DEBUG", "false").lower() == "true"
BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "fa")

# Admin configuration
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",") if os.getenv("ADMIN_IDS") else []
ADMINS = ADMIN_IDS  # Alias for backward compatibility


# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "chart_postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASS = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DATABASE = os.getenv("POSTGRES_TELEGRAM_DB", "telegramdb")

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL")
REDIS_EXPIRE_TIME = int(os.getenv("REDIS_EXPIRE_TIME", "36000"))
APP_NAMESPACE = os.getenv("APP_NAMESPACE", "chapar_bot")


# API configuration
API_ENDPOINT = os.getenv("FASTAPI_ENDPOINT")
ACCESS_TOKEN = os.getenv("FASTAPI_ACCESS_TOKEN")
ADMIN_ACCESS_TOKEN = (
    os.getenv("FASTAPI_ADMIN_ACCESS_TOKEN")
    or os.getenv("CHARTIST_ADMIN_API_KEY")
    or ACCESS_TOKEN
)

# OpenAI-compatible LLM configuration (OpenRouter by default)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
LLM_API_KEY_CHAT = os.getenv("LLM_API_KEY_CHAT") or LLM_API_KEY
LLM_MODEL = os.getenv("LLM_MODEL")
LLM_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL") or LLM_MODEL
LLM_ANALYSIS_MODEL = os.getenv("LLM_ANALYSIS_MODEL") or LLM_MODEL
LLM_NEWS_MODEL = os.getenv("LLM_NEWS_MODEL") or LLM_MODEL
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
LLM_MAX_HISTORY_MESSAGES = int(os.getenv("LLM_MAX_HISTORY_MESSAGES", "20"))
LLM_SYSTEM_PROMPT = os.getenv(
    "LLM_SYSTEM_PROMPT",
    "You are a helpful financial assistant. Respond in Persian unless the user asks for another language.",
)
LLM_HTTP_REFERER = os.getenv("LLM_HTTP_REFERER")
LLM_APP_NAME = os.getenv("LLM_APP_NAME", "Chapar")

# Brave Search API configuration
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY")

# Bot messages
BOT_HELP_LINK = os.getenv("BOT_HELP_LINK", "")
BOT_TUTORIAL_LINK = os.getenv("BOT_TUTORIAL_LINK", "")
BOT_BRAND_HANDLE = os.getenv("BOT_BRAND_HANDLE", "@Chapar_bot")
BOT_RESULTS_CHANNEL = os.getenv("BOT_RESULTS_CHANNEL", "@Chapar_channel")

# Force join channels
FORCE_JOIN_CHANNEL_ID = os.getenv("FORCE_JOIN_CHANNEL_ID", "")
FORCE_JOIN_CHANNEL_LINK = os.getenv("FORCE_JOIN_CHANNEL_LINK", "")
FORCE_JOIN_CHANNEL_TITLE = os.getenv("FORCE_JOIN_CHANNEL_TITLE", "")

# Second force join channel
FORCE_JOIN_CHANNEL_2_ID = os.getenv("FORCE_JOIN_CHANNEL_2_ID", "")
FORCE_JOIN_CHANNEL_2_LINK = os.getenv("FORCE_JOIN_CHANNEL_2_LINK", "")
FORCE_JOIN_CHANNEL_2_TITLE = os.getenv("FORCE_JOIN_CHANNEL_2_TITLE", "")


# Static messages
STATIC_MESSAGES_CHANNEL_ID = os.getenv("STATIC_MESSAGES_CHANNEL_ID", "")
SM_GUIDE_ID = _safe_int_env("SM_GUIDE_ID") # آموزش صرافی و ترید
SM_GOLD_ID = _safe_int_env("SM_GOLD_ID") # تحلیل طلا
SM_DOLLAR_ID = _safe_int_env("SM_DOLLAR_ID") # تحلیل دلار
SM_INCREASE_CREDIT_ID = _safe_int_env("SM_INCREASE_CREDIT_ID") # افزایش اعتبار
SM_PRIZE_ID = _safe_int_env("SM_PRIZE_ID") # جایزه

PLAN_PACKAGES_DAYS = _positive_int_list_env("PLAN_PACKAGES_DAYS")

# Channel configuration
MAIN_CHANNEL = os.getenv("MAIN_CHANNEL", "")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "")

# Exchange configuration
TOOBIT_API_KEY = os.getenv("TOOBIT_API_KEY", "")
TOOBIT_SECRET_KEY = os.getenv("TOOBIT_SECRET_KEY", "")
EXCHANGE_INVITATION_LINK = os.getenv("EXCHANGE_INVITATION_LINK", "")
EXCHANGE_UID_VERIFICATION_URL = os.getenv("EXCHANGE_UID_VERIFICATION_URL", "")
EXCHANGE_INVITATION_CODE = os.getenv("EXCHANGE_INVITATION_CODE", "")


def is_ai_chat_configured() -> bool:
    """Check if AI chat LLM requirements are met."""
    key = os.getenv("LLM_API_KEY_CHAT") or os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("LLM_CHAT_MODEL") or os.getenv("LLM_MODEL")
    return bool(key and key.strip() and model and model.strip())


def is_chart_analysis_configured() -> bool:
    """Check if chart analysis LLM requirements are met."""
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("LLM_ANALYSIS_MODEL") or os.getenv("LLM_MODEL")
    return bool(key and key.strip() and model and model.strip())


def is_news_analysis_configured() -> bool:
    """Check if news analysis (Brave search + LLM) requirements are met."""
    brave_key = os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY")
    llm_key = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("LLM_NEWS_MODEL") or os.getenv("LLM_MODEL")
    return bool(brave_key and brave_key.strip() and llm_key and llm_key.strip() and model and model.strip())


def is_toobit_verification_configured() -> bool:
    """Check if Toobit UID verification requirements are met."""
    link = os.getenv("EXCHANGE_INVITATION_LINK", "")
    key = os.getenv("TOOBIT_API_KEY", "")
    return bool(link and link.strip() and key and key.strip())
