import os

import pytest
import pytest_asyncio


test_database_url = os.getenv("TEST_DATABASE_URL")
if not test_database_url:
    pytest.skip(
        "Set TEST_DATABASE_URL to run PostgreSQL integration tests",
        allow_module_level=True,
    )

os.environ["DATABASE_URL"] = test_database_url
for name in (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
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

from app.utils.db_init import check_database_connection, init_db
from app.models.database import async_engine


pytestmark = pytest.mark.integration


@pytest_asyncio.fixture(autouse=True)
async def dispose_connections_after_test():
    """Do not reuse asyncpg pooled connections across pytest event loops."""
    yield
    await async_engine.dispose()


@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initialization against an explicitly configured database."""
    await init_db()
    assert await check_database_connection() is True


@pytest.mark.asyncio
async def test_database_connection():
    """Test connectivity against an explicitly configured database."""
    assert await check_database_connection() is True
