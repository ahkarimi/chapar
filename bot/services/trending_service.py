import aiohttp
import json
import logging
from typing import List, Dict, Any

from database.cache import CacheManager
from database.cache_config import TRENDING_CACHE_TTL
from crypto_symbols import CRYPTO_SYMBOLS

logger = logging.getLogger(__name__)

CACHE_KEY = "trending_coins"
COINGECKO_URL = "https://api.coingecko.com/api/v3/search/trending"


def _extract_coins(data: dict) -> List[Dict[str, Any]]:
    """Extract and simplify trending coin data from CoinGecko response."""
    coins = data.get("coins", [])
    result = []
    for coin in coins:
        item = coin.get("item", {})
        symbol = (item.get("symbol") or "").upper()
        if symbol not in CRYPTO_SYMBOLS:
            continue
        price_data = item.get("data") or {}
        price_change = price_data.get("price_change_percentage_24h") or {}
        content = price_data.get("content") or {}
        result.append({
            "name": item.get("name", ""),
            "symbol": symbol,
            "market_cap_rank": item.get("market_cap_rank"),
            "price": price_data.get("price"),
            "price_change_percentage_24h_usd": price_change.get("usd"),
            "total_volume": price_data.get("total_volume", ""),
            "content_title": content.get("title", ""),
            "content_description": content.get("description", ""),
        })
    return result


async def get_trending_coins() -> List[Dict[str, Any]]:
    """Get trending coins from cache or CoinGecko API.

    Returns cached data if available, otherwise fetches from API,
    caches for TRENDING_CACHE_TTL seconds, and returns.
    Returns empty list on any failure.
    """
    try:
        cached = await CacheManager.get(CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Cache read error for trending: {e}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(COINGECKO_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.error(f"CoinGecko trending API returned status {resp.status}")
                    return []
                data = await resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch trending coins: {e}")
        return []

    coins = _extract_coins(data)

    try:
        await CacheManager.set(CACHE_KEY, json.dumps(coins), expire=TRENDING_CACHE_TTL)
    except Exception as e:
        logger.warning(f"Cache write error for trending: {e}")

    return coins


def get_trending_coins_sync() -> List[Dict[str, Any]]:
    """Synchronous version for non-async contexts.

    Returns cached data if available, otherwise fetches from API,
    caches for TRENDING_CACHE_TTL seconds, and returns.
    Returns empty list on any failure.
    """
    import requests

    try:
        cached = CacheManager.get_sync(CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Sync cache read error for trending: {e}")

    try:
        resp = requests.get(COINGECKO_URL, timeout=15)
        if resp.status_code != 200:
            logger.error(f"CoinGecko trending API returned status {resp.status_code}")
            return []
        data = resp.json()
    except Exception as e:
        logger.error(f"Failed to fetch trending coins (sync): {e}")
        return []

    coins = _extract_coins(data)

    try:
        CacheManager.set_sync(CACHE_KEY, json.dumps(coins), expire=TRENDING_CACHE_TTL)
    except Exception as e:
        logger.warning(f"Sync cache write error for trending: {e}")

    return coins
