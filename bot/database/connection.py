import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
import logging
import contextlib

Base = declarative_base()

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Database connection handler using SQLAlchemy async."""

    def __init__(self, host, user, password, database, port=5432):
        """Initialize database connection parameters.

        Args:
            host (str): PostgreSQL host
            user (str): PostgreSQL username
            password (str): PostgreSQL password
            database (str): PostgreSQL database name
            port (int): PostgreSQL port, defaults to 5432
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.engine = None
        self.session_factory = None

    async def start(self):
        """Establish connection to the database and ensure tables exist."""
        try:
            # Create async engine with connection pooling
            connection_url = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self.engine = create_async_engine(
                connection_url,
                pool_size=20,
                max_overflow=30,
                pool_timeout=10,
                pool_recycle=300,
                echo=False,
            )

            # Create session factory
            self.session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # Create tables if they don't exist (fallback in case migrations fail)
            # This ensures the application can run even if migrations have issues
            try:
                logger.info("Ensuring required database tables exist...")
                async with self.engine.begin() as conn:
                    # Check if tables should be created
                    await conn.run_sync(Base.metadata.create_all)
                    # create_all does not add columns to an existing installation.
                    await conn.execute(text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(2)"
                    ))
                logger.info("Database tables check completed")
            except Exception as table_error:
                logger.error(f"Error checking/creating tables: {table_error}")
                # Continue anyway to allow the application to start

            return True
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise e

    def get_session(self):
        """Get a new database session as an async context manager.

        Returns:
            AsyncSession: SQLAlchemy async session
        """
        @contextlib.asynccontextmanager
        async def _get_session():
            if not self.session_factory:
                await self.start()

            session = self.session_factory()
            try:
                yield session
            finally:
                await session.close()

        return _get_session()

    async def backup(self):
        """Create a database backup SQL script.

        This is a placeholder for the previous backup functionality.
        For a proper backup with SQLAlchemy, you should use database tools like pg_dump.

        Returns:
            str: Message indicating proper backup method
        """
        return "For proper database backups, use pg_dump or a dedicated backup tool."

# For backward compatibility
Connection = DatabaseConnection
