from sqlalchemy import create_engine # Add synchronous engine import
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Asynchronous Engine and Session
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=24,               # Optimized for 8 CPU cores (8*3)
    max_overflow=50,            # Allow more overflow for high traffic
    pool_timeout=30,            # Connection timeout in seconds
    pool_recycle=1800,          # Recycle connections after 30 minutes
    pool_pre_ping=True,         # Validate connections before using
    connect_args={"timeout": 15},  # Connection timeout
)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Synchronous Engine and Session (for Celery tasks)
sync_engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", ""), # Remove asyncpg dialect if present for sync engine
    echo=False,
    pool_size=5, # Smaller pool for sync tasks usually okay
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session: # Use the correctly named async session
        try:
            yield session
        finally:
            await session.close()
