from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

class BaseExchangeProvider(ABC):
    """
    Abstract Base Class / Interface for Market Data Providers.
    All data providers must implement get_data returning a pandas DataFrame
    with standard OHLCV columns: ['open', 'close', 'high', 'low', 'volume']
    indexed by datetime ('date').
    """

    @abstractmethod
    def get_data(
        self,
        symbol: str,
        period: str,
        interval: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        pass


# Alias for backward compatibility across existing codebase
MarketDataProvider = BaseExchangeProvider

