import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
from app.providers.market_data_provider import MarketDataProvider

logger = logging.getLogger(__name__)


class ToobitDataProvider(MarketDataProvider):
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_candlestick_data(
        self,
        symbol: str,
        interval: str,
        limit: int = 250,
        start_time: int = None,
        end_time: int = None,
    ) -> list:
        """
        Fetch candlestick (kline) data from the Toobit API with retry support.
        Enhanced error handling logs server responses when requests fail.
        """
        url = "https://api.toobit.com/quote/v1/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        logger.info(
            f"Fetching candlestick data: symbol={symbol}, interval={interval}, params={params}"
        )
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()  # Raises HTTPError for bad status codes
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(
                f"HTTP error occurred: {http_err}. Server response: {response.text}"
            )
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

    def _convert_period_to_dates(self, period: str):
        """
        Convert a period string (e.g., '1y', '6m', '2w', '10d') to a start and end date.
        """
        end_date = datetime.now()
        num = int(period[:-1])
        unit = period[-1]
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
        period: str,
        interval: str,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        """
        Fetch candlestick data from the Toobit API and return a transformed DataFrame.

        If a period is provided (and explicit dates are not), it converts the period to a start_date and end_date.
        The resulting DataFrame will have the following columns:
            open, close, high, low, volume
        with the index set to the datetime converted from open_time.
        """
        # If a period is provided and dates are not, convert the period to start_date and end_date.
        if period and (start_date is None or end_date is None):
            start_date, end_date = self._convert_period_to_dates(period)

        # Convert datetime objects to milliseconds timestamps if available.
        start_ts = int(start_date.timestamp() * 1000) if start_date else None
        end_ts = int(end_date.timestamp() * 1000) if end_date else None

        # Fetch raw candlestick data from the API (limit is handled internally).
        raw_data = self._fetch_candlestick_data(
            symbol, interval, start_time=start_ts, end_time=end_ts
        )
        if raw_data is None or len(raw_data) == 0:
            raise ValueError("No data returned from the API.")

        # Create DataFrame.
        df = pd.DataFrame(
            raw_data,
            columns=[
                "open_time",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
            ]
            + [f"col_{i}" for i in range(len(raw_data[0]) - 6)],
        )
        df = df[
            [
                "open_time",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
            ]
        ]

        # Convert 'open_time' from timestamp (ms) to datetime and set as index.
        try:
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        except Exception as e:
            logger.warning(f"open_time conversion failed: {e}")
        df.set_index("open_time", inplace=True)
        df.index.name = "date"

        # Rename columns as required.
        df.rename(
            columns={
                "open_price": "open",
                "close_price": "close",
                "high_price": "high",
                "low_price": "low",
            },
            inplace=True,
        )

        # Reorder columns to match: "open", "close", "high", "low", "volume"
        df = df[["open", "close", "high", "low", "volume"]]

        # Convert numeric columns from strings to numeric types.
        for col in ["open", "close", "high", "low", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Sort the DataFrame index in ascending order.
        df.sort_index(inplace=True)

        return df
