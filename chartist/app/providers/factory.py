import re
import logging
from typing import Dict, Type
from app.config import settings
from app.providers.market_data_provider import MarketDataProvider
from app.providers.toobit_data_provider import ToobitDataProvider
from app.providers.bourse_provider import SourcearenaDataProvider
from app.providers.yahoo_data_provider import YahooDataProvider
from app.providers.binance_data_provider import BinanceDataProvider
from app.providers.fallback_provider import FallbackMarketDataProvider

logger = logging.getLogger(__name__)

PROVIDERS: Dict[str, Type[MarketDataProvider]] = {
    "toobit": ToobitDataProvider,
    "sourcearena": SourcearenaDataProvider,
    "binance": BinanceDataProvider,
    "yahoo": YahooDataProvider,
    "yfinance": YahooDataProvider,
}


def get_provider(name: str) -> MarketDataProvider:
    """
    Instantiate a market data provider by name.
    """
    key = name.strip().lower()
    provider_cls = PROVIDERS.get(key)
    if not provider_cls:
        logger.warning(
            f"Unknown provider '{name}'. Falling back to BinanceDataProvider."
        )
        return BinanceDataProvider()
    return provider_cls()


def get_provider_for_symbol(symbol: str) -> MarketDataProvider:
    """
    Dynamically resolve the primary and fallback market data providers for a symbol based on configuration.
    """
    is_persian = bool(re.search(r"[\u0600-\u06FF]", symbol))

    if is_persian:
        primary_key = getattr(settings, "STOCK_DATA_PROVIDER", "sourcearena")
        fallback_key = getattr(settings, "FALLBACK_STOCK_PROVIDER", "yahoo")
    else:
        primary_key = getattr(settings, "CRYPTO_DATA_PROVIDER", "toobit")
        fallback_key = getattr(settings, "FALLBACK_CRYPTO_PROVIDER", "binance")

    primary_provider = get_provider(primary_key)

    if not fallback_key or primary_key.lower() == fallback_key.lower():
        return primary_provider

    fallback_provider = get_provider(fallback_key)
    return FallbackMarketDataProvider(primary=primary_provider, fallback=fallback_provider)
