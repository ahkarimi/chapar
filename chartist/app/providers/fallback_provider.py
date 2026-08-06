import pandas as pd
from typing import Optional
from datetime import datetime
import logging
from app.providers.market_data_provider import MarketDataProvider

logger = logging.getLogger(__name__)


class FallbackMarketDataProvider(MarketDataProvider):
    """
    Adapter provider that wraps a primary MarketDataProvider and a fallback MarketDataProvider.
    If the primary provider fails (throws an exception or returns empty data), it seamlessly
    falls back to the secondary provider.
    """

    def __init__(self, primary: MarketDataProvider, fallback: MarketDataProvider):
        self.primary = primary
        self.fallback = fallback

    def get_data(
        self,
        symbol: str,
        period: str,
        interval: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        primary_name = self.primary.__class__.__name__
        fallback_name = self.fallback.__class__.__name__

        try:
            logger.info(
                f"Attempting to fetch data with primary provider: {primary_name} for symbol: {symbol}"
            )
            df = self.primary.get_data(symbol, period, interval, start_date, end_date)
            if df is not None and not df.empty:
                return df
            logger.warning(
                f"Primary provider {primary_name} returned empty data for {symbol}. Attempting fallback."
            )
        except Exception as e:
            logger.warning(
                f"Primary provider {primary_name} failed for symbol {symbol}: {e}. Falling back to {fallback_name}."
            )

        # Attempt fallback provider
        try:
            logger.info(
                f"Attempting to fetch data with fallback provider: {fallback_name} for symbol: {symbol}"
            )
            df_fallback = self.fallback.get_data(
                symbol, period, interval, start_date, end_date
            )
            if df_fallback is not None and not df_fallback.empty:
                logger.info(
                    f"Successfully fetched data for symbol {symbol} using fallback provider: {fallback_name}"
                )
                return df_fallback
            raise ValueError(
                f"Fallback provider {fallback_name} returned empty data for {symbol}"
            )
        except Exception as fallback_err:
            logger.error(
                f"Both primary ({primary_name}) and fallback ({fallback_name}) providers failed for symbol {symbol}: {fallback_err}"
            )
            raise fallback_err
