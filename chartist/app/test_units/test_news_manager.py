import asyncio
import os


for name in (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "DATABASE_URL",
    "REDIS_URL",
    "APP_NAMESPACE",
    "STOCK_API_KEY",
    "TOOBIT_API_KEY",
    "TOOBIT_SECRET_KEY",
    "CHARTIST_API_KEY",
    "CHARTIST_ADMIN_API_KEY",
    "SOURCEARENA_TOKEN",
    "DOCS_USERNAME",
    "DOCS_PASSWORD",
):
    os.environ.setdefault(name, "test")
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@127.0.0.1:5432/test"

from app.schemas.news import NewsMethod, NewsRequest
from app.services.news_manager import NewsManager


class FakeBraveNewsService:
    def __init__(self):
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        return [{"title": "BTC headline", "url": "https://example.com/btc"}]


class FakeLLMService:
    def __init__(self):
        self.calls = []

    async def get_news(self, **kwargs):
        self.calls.append(kwargs)
        return {"answer": "Grounded summary", "metadata": {}}


class FakeCacheManager:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value, expire):
        self.values[key] = value


def test_manager_fetches_sources_before_summarizing():
    brave = FakeBraveNewsService()
    llm = FakeLLMService()
    cache = FakeCacheManager()
    manager = NewsManager(llm, cache, brave)

    result = asyncio.run(
        manager.get_news(NewsRequest(symbol="BTC", method=NewsMethod.SUMMARY_SITES))
    )

    assert brave.queries == ["Bitcoin (BTC)"]
    assert llm.calls[0]["sources"] == result["sources"]
    assert result["news"]["answer"] == "Grounded summary"
    assert any(key.startswith("news:v2:BTC:summary_sites") for key in cache.values)
