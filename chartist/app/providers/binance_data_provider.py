import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tenacity import retry, stop_after_attempt, wait_fixed
from typing import Optional
import logging
from app.providers.market_data_provider import MarketDataProvider

logger = logging.getLogger(__name__)


class BinanceDataProvider(MarketDataProvider):
    """
    Data provider for fetching public market candlestick data from Binance Public API.
    Does not require API keys or credentials.
    """

    PRIMARY_URL = "https://api.binance.com/api/v3/klines"
    FALLBACK_URL = "https://data-api.binance.vision/api/v3/klines"

    INTERVAL_MAP = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "6h": "6h",
        "8h": "8h",
        "12h": "12h",
        "1d": "1d",
        "1w": "1w",
        "1M": "1M",
    }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_candlestick_data(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> list:
        """
        Fetch kline data from Binance public API.
        """
        binance_interval = self.INTERVAL_MAP.get(interval, "1d")
        # Format symbol for Binance (e.g. BTC/USDT -> BTCUSDT, btc-usdt -> BTCUSDT)
        formatted_symbol = symbol.replace("/", "").replace("-", "").replace("_", "").upper()

        params = {"symbol": formatted_symbol, "interval": binance_interval, "limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        logger.info(
            f"Fetching Binance candlestick data: symbol={formatted_symbol}, interval={binance_interval}, params={params}"
        )

        for url in [self.PRIMARY_URL, self.FALLBACK_URL]:
            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as err:
                logger.warning(f"Binance request failed on {url}: {err}")
                continue

        raise RuntimeError(f"Failed to fetch data from Binance API for symbol {symbol}")

    def _convert_period_to_dates(self, period: str):
        """
        Convert a period string (e.g., '1y', '6m', '2w', '10d') to a start and end date.
        """
        end_date = datetime.now()
        period_lower = period.strip().lower()
        num = int(period_lower[:-1])
        unit = period_lower[-1]
        if unit == "y":
            start_date = end_date - relativedelta(years=num)
        elif unit == "m":
            start_date = end_date - relativedelta(months=num)
        elif unit == "w":
            start_date = end_date - relativedelta(weeks=num)
        elif unit == "d":
            start_date = end_date - relativedelta(days=num)
        else:
            raise ValueError(
                "Invalid period format. Use formats like '1y', '6m', '2w', or '10d'."
            )
        return start_date, end_date

    def get_data(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Fetch candlestick data from Binance API and return a transformed DataFrame.
        """
        if period and (start_date is None or end_date is None):
            start_date, end_date = self._convert_period_to_dates(period)

        start_ts = int(start_date.timestamp() * 1000) if start_date else None
        end_ts = int(end_date.timestamp() * 1000) if end_date else None

        raw_data = self._fetch_candlestick_data(
            symbol, interval, start_time=start_ts, end_time=end_ts
        )

        if not raw_data or len(raw_data) == 0:
            raise ValueError(f"No data returned from Binance for symbol {symbol}")

        # Binance kline structure:
        # [
        #   [
        #     1499040000000,      // Open time
        #     "0.01634790",       // Open
        #     "0.80000000",       // High
        #     "0.01575800",       // Low
        #     "0.01577100",       // Close
        #     "148976.11427815",  // Volume
        #     1499040959999,      // Close time
        #     ...
        #   ]
        # ]
        df = pd.DataFrame(
            raw_data,
            columns=[
                "open_time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "close_time",
                "quote_asset_volume",
                "number_of_trades",
                "taker_buy_base_asset_volume",
                "taker_buy_quote_asset_volume",
                "ignore",
            ],
        )

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df.set_index("open_time", inplace=True)
        df.index.name = "date"

        df = df[["open", "close", "high", "low", "volume"]].copy()

        for col in ["open", "close", "high", "low", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df.sort_index(inplace=True)
        return df
