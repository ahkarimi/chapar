import asyncio
import json
import logging
from typing import Any, Dict, Optional

from app.services.brave_news_service import BraveNewsService
from app.core.cache import CacheManager
from app.core.json_loader import load_json_file
from app.schemas.news import NewsMethod, NewsRequest
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class NewsManager:
    def __init__(
        self,
        llm_service: LLMService,
        cache_manager: CacheManager,
        brave_news_service: Optional[BraveNewsService] = None,
    ):
        self.llm_service = llm_service
        self.cache_manager = cache_manager
        self.brave_news_service = brave_news_service or BraveNewsService()
        # Load settings from data.json
        try:
            self.data = load_json_file("data.json")
            self.cache_expiration = self.data.get("redis_expiration", {}).get("news_summary", 86400)
            # Load symbol mapping from data.json
            self.symbol_map = self.data.get("valid_symbols", {})
        except Exception as e:
            print(f"Warning: Failed to load data from JSON file: {e}")
            self.cache_expiration = 86400  # Default to 1 day if loading fails
            # Fallback symbol map if loading fails
            self.symbol_map = {
                "BTC": "Bitcoin",
                "ETH": "Ethereum",
                "ADA": "Cardano"
            }

    def _generate_default_query(self, symbol: str, method: NewsMethod) -> str:
        """Generate a default query based on the symbol and method."""
        # Use symbol map from data.json
        full_name = self.symbol_map.get(symbol.upper(), symbol)

        # Generate different queries based on the method
        if method == NewsMethod.SUMMARY_SITES:
            return f"{full_name} ({symbol.upper()})"
        elif method == NewsMethod.SUMMARY_SOCIAL:
            return f"{full_name} ({symbol.upper()})"
        elif method == NewsMethod.SENTIMENT_SITES:
            return f"{full_name} ({symbol.upper()})"
        elif method == NewsMethod.SENTIMENT_SOCIAL:
            return f"{full_name} ({symbol.upper()})"
        else:
            return f"{full_name} ({symbol.upper()})"

    async def get_news(self, request: NewsRequest) -> Dict[str, Any]:
        """
        Get news for a specific symbol and method:
        1. Generate or use provided query
        2. Check cache
        3. Get news from LLM with specific method
        4. Cache and return results
        """
        # Step 1: Create a cache key based on the request
        cache_key = f"news:v2:{request.symbol}:{request.method.value}:{request.response_language}:{request.query or 'default'}"

        # Try to fetch result from the cache
        cached_result = await self.cache_manager.get(cache_key)
        if cached_result:
            return json.loads(cached_result)

        # Step 2: Generate or use provided query
        query = request.query or self._generate_default_query(request.symbol, request.method)

        # Step 3: Fetch current news, then give those sources to the LLM.
        sources = await asyncio.to_thread(self.brave_news_service.search, query)
        news_response = await self.llm_service.get_news(
            query=query,
            symbol=request.symbol,
            method=request.method.value,
            sources=sources,
            response_language=request.response_language,
        )

        # Prepare the response
        response = {
            "news": news_response,
            "query": query,
            "method": request.method.value,
            "sources": sources,
        }

        # Step 4: Store the result in cache using expiration from data.json
        await self.cache_manager.set(
            cache_key,
            json.dumps(response),
            expire=self.cache_expiration
        )

        return response

    def get_news_sync(self, request: NewsRequest) -> Dict[str, Any]:
        """
        Synchronous version of get_news for Celery tasks.
        This method uses the synchronous methods of the underlying services.

        Unlike the async version, this implementation explicitly uses synchronous
        cache operations to avoid event loop issues in the Celery worker.
        """
        # Step 1: Create a cache key based on the request
        cache_key = f"news:v2:{request.symbol}:{request.method.value}:{request.response_language}:{request.query or 'default'}"

        # Try to fetch result from the cache using synchronous method
        logger.info(f"Checking sync cache for key: {cache_key}")
        cached_result = self.cache_manager.get_sync(cache_key)
        if cached_result:
            logger.info(f"Sync cache hit for {cache_key}")
            return json.loads(cached_result)

        # Step 2: Generate or use provided query
        query = request.query or self._generate_default_query(request.symbol, request.method)

        # Step 3: Fetch current news, then create an event loop just for the LLM call.
        sources = self.brave_news_service.search(query)
        loop = asyncio.new_event_loop()
        try:
            # Only use the event loop for the LLM call, not cache operations
            news_response = loop.run_until_complete(
                self.llm_service.get_news(
                    query=query,
                    symbol=request.symbol,
                    method=request.method.value,
                    sources=sources,
                    response_language=request.response_language,
                )
            )
        finally:
            loop.close()

        # Prepare the response
        response = {
            "news": news_response,
            "query": query,
            "method": request.method.value,
            "sources": sources,
        }

        # Step 4: Store the result in cache using synchronous method
        try:
            self.cache_manager.set_sync(
                cache_key,
                json.dumps(response),
                expire=self.cache_expiration
            )
            logger.info(f"Set sync cache for key: {cache_key} with expiration: {self.cache_expiration}s")
        except Exception as e:
            logger.error(f"Failed to set sync cache for {cache_key}: {e}")

        return response
