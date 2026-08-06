import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Any
from app.config import settings  # expects settings.SOURCEARENA_TOKEN
from app.providers.market_data_provider import MarketDataProvider
from tenacity import retry, stop_after_attempt, wait_fixed
import logging
import jdatetime

logger = logging.getLogger(__name__)


def convert_period_to_days(period: str) -> int:
    """
    Convert a period string to a number of days.
    Assumptions:
      - '1y' = 365 days,
      - '1m' = 30 days,
      - '1w' = 7 days,
      - '30d' means 30 days.
    """
    period = period.strip().lower()
    if period.endswith("y"):
        return int(float(period[:-1]) * 365)
    elif period.endswith("m"):
        return int(float(period[:-1]) * 30)
    elif period.endswith("w"):
        return int(float(period[:-1]) * 7)
    elif period.endswith("d"):
        return int(period[:-1])
    else:
        # Assume the period is given in days if no suffix provided
        return int(period)


def convert_shamsi_to_gregorian(date_str: str) -> datetime:
    """
    Convert a Persian (Shamsi) date string in 'YYYY/MM/DD' format to a Gregorian datetime.
    """
    try:
        jd = jdatetime.datetime.strptime(date_str, "%Y/%m/%d")
        return jd.togregorian()
    except Exception as e:
        logger.error(f"Error converting date {date_str}: {e}")
        return pd.NaT


class SourcearenaDataProvider(MarketDataProvider):
    BASE_URL = "https://sa.resicard.ir/api/"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch_stock_data(
        self,
        symbol: str,
        period: Optional[str] = "1y",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Any:
        """
        Fetch historical price data for a given symbol from Sourcearena.
        If both start_date and end_date are provided, compute days from the range;
        otherwise, convert the period (e.g. '1y') into a number of days.
        """
        logger.info(
            f"Fetching Sourcearena data: symbol={symbol}, period={period}, "
            f"start_date={start_date}, end_date={end_date}"
        )

        try:
            if start_date and end_date:
                days = (end_date - start_date).days + 1  # include both dates
            else:
                days = convert_period_to_days(period)
            logger.debug(f"Computed days={days} for symbol={symbol}")

            params = {
                "token": settings.SOURCEARENA_TOKEN,
                "name": symbol,
                "days": days,
            }

            try:
                response = requests.get(self.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as req_err:
                logger.error(
                    "HTTP error when fetching data for symbol=%s: %s", symbol, req_err
                )
                raise

            try:
                data = response.json()
            except Exception as json_err:
                logger.error("JSON decode error for symbol=%s: %s", symbol, json_err)
                raise

            if not isinstance(data, list) or len(data) == 0:
                error_msg = f"No data returned for symbol {symbol} with params {params}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(
                "Data successfully fetched from Sourcearena for symbol=%s", symbol
            )

            # Convert JSON list to DataFrame
            df = pd.DataFrame(data)

            # Rename fields to standard OHLCV names (keeping date for index)
            df = df.rename(
                columns={
                    "first_price": "open",
                    "close_price": "close",
                    "highest_price": "high",
                    "lowest_price": "low",
                    "trade_volume": "volume",
                    "date": "date",
                }
            )

            # Convert numeric columns from strings to numeric types
            for col in ["open", "close", "high", "low", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # Convert the 'date' column from Shamsi to Gregorian datetime and set as index
            df["date"] = df["date"].apply(convert_shamsi_to_gregorian)
            df.set_index("date", inplace=True)

            # Ensure only OHLCV columns remain
            df = df[["open", "close", "high", "low", "volume"]]

            # Sort the DataFrame index in ascending order
            df = df.sort_index()

            # Fill 'open': if NaN or 0, use yesterday's close
            df["open"] = df["open"].mask(
                (df["open"].isna()) | (df["open"] == 0), df["close"].shift(1)
            )
            # Fill 'high': if NaN or 0, use the maximum of open, close, and low in that row
            df["high"] = df["high"].mask(
                (df["high"].isna()) | (df["high"] == 0),
                df[["open", "close", "low"]].max(axis=1),
            )
            # Fill 'low': if NaN or 0, use the minimum of open, close, and high in that row
            df["low"] = df["low"].mask(
                (df["low"].isna()) | (df["low"] == 0),
                df[["open", "close", "high"]].min(axis=1),
            )
            # Fill 'close': if NaN or 0, use tomorrow's open (next row)
            df["close"] = df["close"].mask(
                (df["close"].isna()) | (df["close"] == 0), df["open"].shift(-1)
            )

            logger.info("DataFrame processed successfully for symbol=%s", symbol)
            return df

        except Exception as e:
            logger.exception("Error in _fetch_stock_data for symbol=%s: %s", symbol, e)
            raise

    def get_data(
        self,
        symbol: str,
        period: str,
        interval: str,  # interval is ignored because Sourcearena returns only daily data
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Any:
        """
        Public method to fetch data for a given symbol.
        The interval parameter is ignored.
        """
        try:
            return self._fetch_stock_data(symbol, period, start_date, end_date)
        except Exception as e:
            logger.error("Error in get_data for symbol=%s: %s", symbol, e)
            raise
