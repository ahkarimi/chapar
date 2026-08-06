import logging
import time
from typing import Any, Dict, List, Optional

import requests

from app.config import settings

logger = logging.getLogger(__name__)


class BraveNewsService:
    """Fetch and normalize news results from Brave Search."""

    SEARCH_URL = "https://api.search.brave.com/res/v1/news/search"

    def __init__(
        self,
        api_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        timeout: float = 10.0,
    ):
        self.api_key = api_key or settings.BRAVE_SEARCH_API_KEY
        self.session = session or requests.Session()
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.timeout = timeout

    def search(
        self,
        query: str,
        suffix: str = "crypto news",
        count: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return Brave news results suitable for sending to the summarizer."""
        if not self.api_key:
            raise ValueError("BRAVE_SEARCH_API_KEY (or BRAVE_API_KEY) must be configured")

        search_query = " ".join(part.strip() for part in (query, suffix) if part.strip())
        params = {
            "q": search_query,
            "count": count,
            "country": "us",
            "search_lang": "en",
            "spellcheck": 1,
        }
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

        last_exception: Optional[Exception] = None
        for retry_count in range(self.max_retries):
            try:
                response = self.session.get(
                    self.SEARCH_URL,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ValueError("Brave Search returned invalid JSON") from exc

                results = payload.get("results")
                if not isinstance(results, list):
                    raise ValueError("Brave Search response did not contain a results list")
                if not results:
                    raise ValueError(f"Brave Search found no news for query: {search_query}")

                return [
                    {
                        "title": entry.get("title") or "No title available",
                        "url": entry.get("url") or "",
                        "description": entry.get("description") or "No description available",
                        "published_at": entry.get("page_age") or entry.get("age"),
                    }
                    for entry in results
                    if isinstance(entry, dict)
                ]
            except requests.exceptions.RequestException as exc:
                last_exception = exc
                if retry_count + 1 < self.max_retries:
                    backoff = self.initial_backoff * (2**retry_count)
                    logger.warning(
                        "Brave news request failed; retrying in %.1fs (%d/%d)",
                        backoff,
                        retry_count + 1,
                        self.max_retries,
                    )
                    time.sleep(backoff)

        raise RuntimeError(
            f"Failed to fetch Brave news after {self.max_retries} attempts: {last_exception}"
        ) from last_exception
