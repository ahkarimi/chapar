import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text
from urllib.parse import urlparse
import logging
import os
import asyncio
import time  # Import time for sleep

from app.config import settings
from app.models.database import Base, async_engine

logger = logging.getLogger(__name__)

# Define a lock file path (adjust as needed, e.g., use a temp dir)
LOCK_FILE_PATH = "/tmp/db_init.lock"
LOCK_TIMEOUT = 10  # seconds to wait for the lock

async def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    parsed = urlparse(settings.DATABASE_URL)
    db_name = parsed.path.lstrip('/')

    # Create connection string for postgres default database
    default_db_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"

    try:
        # Connect to default postgres database
        conn = await asyncpg.connect(default_db_url)

        # Check if our database exists
        result = await conn.fetch(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )

        if not result:
            logger.info(f"Creating database {db_name}")
            # Create database if it doesn't exist
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database {db_name} created successfully")
        else:
            logger.info(f"Database {db_name} already exists")

        await conn.close()

    except Exception as e:
        logger.error(f"Error during database creation: {str(e)}")
        raise

async def check_tables_exist():
    """Check if all tables exist, if not create them"""
    try:
        async with async_engine.begin() as conn:
            # Create all tables defined in models, checking first if they exist
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
            logger.info("All tables created successfully")
    except Exception as e:
        logger.error(f"Error during table creation: {str(e)}")
        raise

async def check_database_connection():
    """Test database connection"""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

async def init_db():
    """Initialize database and tables, ensuring only one worker does it."""
    lock_acquired = False
    start_time = time.monotonic()

    while time.monotonic() - start_time < LOCK_TIMEOUT:
        try:
            # Attempt to create the lock file exclusively
            # os.O_CREAT | os.O_EXCL ensures atomic creation
            fd = os.open(LOCK_FILE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            lock_acquired = True
            logger.info(f"Worker {os.getpid()} acquired DB init lock.")
            break  # Lock acquired, exit loop
        except FileExistsError:
            logger.info(f"Worker {os.getpid()} waiting for DB init lock...")
            await asyncio.sleep(0.5) # Wait before retrying
        except Exception as e:
            logger.error(f"Error acquiring lock: {e}")
            raise # Propagate other errors

    if not lock_acquired:
        logger.warning(f"Worker {os.getpid()} failed to acquire lock after {LOCK_TIMEOUT}s. Assuming DB is initialized.")
        return # Exit if lock couldn't be acquired (another worker likely succeeded or is stuck)

    try:
        logger.info(f"Worker {os.getpid()} proceeding with DB initialization.")
        # Create database if it doesn't exist
        await create_database_if_not_exists()

        # Create tables if they don't exist
        await check_tables_exist()

        # Test connection
        connection_successful = await check_database_connection()

        if not connection_successful:
            raise Exception("Failed to establish database connection after initialization")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        # Consider whether to re-raise or handle differently if lock was acquired
        raise
    finally:
        # Always remove the lock file if it was acquired by this worker
        if lock_acquired:
            try:
                os.remove(LOCK_FILE_PATH)
                logger.info(f"Worker {os.getpid()} released DB init lock.")
            except OSError as e:
                # Log error if lock removal fails, but don't prevent app start
                logger.error(f"Error removing lock file {LOCK_FILE_PATH}: {e}")
