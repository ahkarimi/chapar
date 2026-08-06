import os

import httpx
import pytest


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
from app.main import app
from app.config import settings


def test_openapi_describes_the_supported_product_api():
    schema = app.openapi()

    assert schema["info"]["title"] == "Chapar API"
    assert "/api/v1/stocks/chart/" in schema["paths"]
    assert "/api/v1/stocks/analyze/" in schema["paths"]
    assert "/api/v1/news/news/" in schema["paths"]
    assert "APIKeyHeader" in schema["components"]["securitySchemes"]


def test_docs_and_schema_are_not_listed_as_public_product_endpoints():
    schema = app.openapi()

    assert "/docs" not in schema["paths"]
    assert "/openapi.json" not in schema["paths"]


@pytest.mark.asyncio
async def test_docs_and_openapi_require_basic_authentication():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/openapi.json")).status_code == 401

        schema_response = await client.get(
            "/openapi.json", auth=(settings.DOCS_USERNAME, settings.DOCS_PASSWORD)
        )
        docs_response = await client.get(
            "/docs", auth=(settings.DOCS_USERNAME, settings.DOCS_PASSWORD)
        )

    assert schema_response.status_code == 200
    assert "/api/v1/stocks/chart/" in schema_response.json()["paths"]
    assert docs_response.status_code == 200
