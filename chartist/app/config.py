import os
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _optional_int(name: str) -> Optional[int]:
    value = os.getenv(name)
    return int(value) if value else None


def _optional_float(name: str) -> Optional[float]:
    value = os.getenv(name)
    return float(value) if value else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    REDIS_URL: str = os.getenv("REDIS_URL")
    REDIS_CHART_EXPIRE: int = int(os.getenv("REDIS_CHART_EXPIRE", 3600))
    REDIS_CURRENCY_EXPIRE: int = int(os.getenv("REDIS_CURRENCY_EXPIRE", 600))
    REDIS_ANALYSIS_EXPIRE: int = int(os.getenv("REDIS_ANALYSIS_EXPIRE", 3600))
    APP_NAMESPACE: str = os.getenv("APP_NAMESPACE")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    LLM_API_KEY: Optional[str] = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    LLM_ANALYSIS_MODEL: Optional[str] = os.getenv("LLM_ANALYSIS_MODEL") or os.getenv("LLM_MODEL")
    LLM_NEWS_MODEL: Optional[str] = os.getenv("LLM_NEWS_MODEL") or os.getenv("LLM_MODEL")
    LLM_RESPONSE_LANGUAGE: str = os.getenv("LLM_RESPONSE_LANGUAGE", "Persian")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "10000"))
    LLM_HTTP_REFERER: Optional[str] = os.getenv("LLM_HTTP_REFERER")
    LLM_APP_NAME: Optional[str] = os.getenv("LLM_APP_NAME")
    BRAVE_SEARCH_API_KEY: Optional[str] = os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY")
    STOCK_API_KEY: str = os.getenv("STOCK_API_KEY")
    TOOBIT_API_KEY: str = os.getenv("TOOBIT_API_KEY")
    TOOBIT_SECRET_KEY: str = os.getenv("TOOBIT_SECRET_KEY")
    TOOBIT_ALLOWED_INVITATION_CODES: str = os.getenv("TOOBIT_ALLOWED_INVITATION_CODES", "")
    REFERRAL_REWARD_DAYS: Optional[int] = _optional_int("REFERRAL_REWARD_DAYS")
    PLAN_PACKAGES_DAYS: str = os.getenv("PLAN_PACKAGES_DAYS", "")
    PLAN_NOTIFICATION_FIRST_RATIO: Optional[float] = _optional_float("PLAN_NOTIFICATION_FIRST_RATIO")
    PLAN_NOTIFICATION_SECOND_RATIO: Optional[float] = _optional_float("PLAN_NOTIFICATION_SECOND_RATIO")
    PLAN_NOTIFICATION_GIFT_DAYS: Optional[int] = _optional_int("PLAN_NOTIFICATION_GIFT_DAYS")
    PLAN_ANALYSIS_COUNT_DISPLAY_THRESHOLD: Optional[int] = _optional_int("PLAN_ANALYSIS_COUNT_DISPLAY_THRESHOLD")
    TRIAL_DURATION_HOURS: Optional[int] = _optional_int("TRIAL_DURATION_HOURS")
    CHARTIST_API_KEY: str = os.getenv("CHARTIST_API_KEY")
    CHARTIST_ADMIN_API_KEY: str = os.getenv("CHARTIST_ADMIN_API_KEY") or os.getenv("CHARTIST_API_KEY")
    JWT_SECRET: Optional[str] = os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    SOURCEARENA_TOKEN: str = os.getenv("SOURCEARENA_TOKEN")
    CRYPTO_DATA_PROVIDER: str = os.getenv("CRYPTO_DATA_PROVIDER", "toobit")
    STOCK_DATA_PROVIDER: str = os.getenv("STOCK_DATA_PROVIDER", "sourcearena")
    FALLBACK_CRYPTO_PROVIDER: str = os.getenv("FALLBACK_CRYPTO_PROVIDER", "binance")
    FALLBACK_STOCK_PROVIDER: str = os.getenv("FALLBACK_STOCK_PROVIDER", "yahoo")
    DOCS_USERNAME: str = os.getenv("DOCS_USERNAME")
    DOCS_PASSWORD: str = os.getenv("DOCS_PASSWORD")

    @field_validator("CHARTIST_API_KEY", "DOCS_USERNAME", "DOCS_PASSWORD")
    @classmethod
    def require_security_value(cls, value: str, info):
        if not value or not value.strip():
            raise ValueError(f"{info.field_name} must be configured")
        return value


settings = Settings()
