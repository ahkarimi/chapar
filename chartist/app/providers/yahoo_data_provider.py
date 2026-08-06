import yfinance as yf
import pandas as pd
from typing import Optional, Any
from datetime import datetime
from app.providers.market_data_provider import MarketDataProvider
from tenacity import retry, stop_after_attempt, wait_fixed
import logging

logger = logging.getLogger(__name__)


class YahooDataProvider(MarketDataProvider):
    def _format_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for Yahoo Finance if needed.
        For example, BTCUSDT -> BTC-USD.
        """
        sym = symbol.strip().upper()
        if sym.endswith("USDT"):
            return f"{sym[:-4]}-USD"
        return sym

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_stock_data(
        self,
        symbol: str,
        period: Optional[str] = "1y",
        interval: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Fetch stock data from yfinance with retry support and standard OHLCV formatting."""
        formatted_symbol = self._format_symbol(symbol)
        logger.info(
            f"Fetching stock data from Yahoo Finance: symbol={symbol} (formatted: {formatted_symbol}), "
            f"period={period}, interval={interval}, start_date={start_date}, end_date={end_date}"
        )

        ticker = yf.Ticker(formatted_symbol)

        if start_date and end_date:
            data = ticker.history(start=start_date, end=end_date, interval=interval)
        else:
            data = ticker.history(period=period, interval=interval)

        if data.empty:
            raise ValueError(f"No data found for symbol {symbol} ({formatted_symbol})")

        # Standardize column names to lowercase
        data = data.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        # Retain standard OHLCV columns
        data = data[["open", "close", "high", "low", "volume"]].copy()

        # Convert columns to numeric types
        for col in ["open", "close", "high", "low", "volume"]:
            data[col] = pd.to_numeric(data[col], errors="coerce")

        data.index.name = "date"
        data.sort_index(inplace=True)

        return data

    def get_data(
        self,
        symbol: str,
        period: str = "1y",
        interval: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Fetch stock data, with consolidated validation and standard OHLCV output."""
        return self._fetch_stock_data(symbol, period, interval, start_date, end_date)
