import os
from unittest.mock import Mock

import pytest
import requests


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

from app.services.brave_news_service import BraveNewsService


def test_search_formats_brave_results():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [
            {
                "title": "Bitcoin rises",
                "url": "https://example.com/story",
                "description": "BTC moved higher.",
                "page_age": "2026-07-31T10:00:00Z",
            }
        ]
    }
    session = Mock()
    session.get.return_value = response
    service = BraveNewsService(api_key="brave-key", session=session)

    results = service.search("Bitcoin (BTC)")

    assert results == [
        {
            "title": "Bitcoin rises",
            "url": "https://example.com/story",
            "description": "BTC moved higher.",
            "published_at": "2026-07-31T10:00:00Z",
        }
    ]
    request = session.get.call_args
    assert request.kwargs["params"]["q"] == "Bitcoin (BTC) crypto news"
    assert request.kwargs["headers"]["X-Subscription-Token"] == "brave-key"
    assert request.kwargs["params"]["count"] == 10


def test_search_retries_request_failures(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [{"title": "Recovered result", "url": "https://example.com"}]
    }
    session = Mock()
    session.get.side_effect = [requests.Timeout("slow"), response]
    monkeypatch.setattr("app.services.brave_news_service.time.sleep", lambda _: None)
    service = BraveNewsService(api_key="brave-key", session=session)

    assert service.search("BTC")[0]["title"] == "Recovered result"
    assert session.get.call_count == 2


def test_search_rejects_empty_results():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": []}
    session = Mock()
    session.get.return_value = response
    service = BraveNewsService(api_key="brave-key", session=session)

    with pytest.raises(ValueError, match="found no news"):
        service.search("BTC")


def test_search_requires_api_key():
    service = BraveNewsService(api_key="", session=Mock())
    service.api_key = None

    with pytest.raises(ValueError, match="BRAVE_SEARCH_API_KEY"):
        service.search("BTC")
