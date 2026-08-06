import json
import logging
import httpx
from typing import Optional, Dict, List, Any
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.core.cache import CacheManager

logger = logging.getLogger(__name__)

class SourceArenaProvider:
    """
    Provider that fetches currency data from SourceArena API.
    Implements caching to improve performance.
    """

    BASE_URL = "https://sa.resicard.ir/api/"

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def _fetch_data(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch currency data from SourceArena API with retry support.

        Args:
            symbol (Optional[str]): Optional symbol/slug to filter results

        Returns:
            Dict[str, Any]: JSON response from the API
        """
        logger.info(f"Fetching data from SourceArena API: symbol={symbol}")

        url = f"{self.BASE_URL}?token={settings.SOURCEARENA_TOKEN}&currency"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # If symbol specified, filter the data
            if symbol and "data" in data:
                filtered_data = [item for item in data["data"] if item.get("slug") == symbol]
                if filtered_data:
                    data["data"] = filtered_data
                else:
                    raise ValueError(f"No data found for symbol {symbol}")

            return data

    async def get_data(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get currency data with caching support.

        Args:
            symbol (Optional[str]): Optional symbol/slug to filter results

        Returns:
            Dict[str, Any]: Currency data
        """
        # Create cache key based on parameters
        cache_key = f"sourcearena:{'all' if symbol is None else symbol}"

        # Try to get from cache first
        cached_data = await CacheManager.get(cache_key)
        if cached_data:
            return json.loads(cached_data)

        # If not in cache, fetch from API
        data = await self._fetch_data(symbol)

        # Cache the result
        await CacheManager.set(
            cache_key,
            json.dumps(data),
            expire=settings.REDIS_CURRENCY_EXPIRE
        )

        return data
