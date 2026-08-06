import redis.asyncio as redis
import redis as redis_sync  # Import synchronous Redis client
from app.config import settings
import logging
import json  # Add json for deserialize method
import asyncio

logger = logging.getLogger(__name__)

# Mapping of asyncio event loops to Redis clients
_redis_clients = {}
# Synchronous Redis client for Celery tasks
sync_redis_client = None

async def get_redis_client():
    """Returns the Redis client for the current event loop, initializing it if necessary."""
    loop = asyncio.get_running_loop()
    client = _redis_clients.get(loop)
    if client is None:
        client = await redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_clients[loop] = client
    return client

def get_sync_redis_client():
    """Returns a synchronous Redis client for use in Celery tasks"""
    global sync_redis_client
    if sync_redis_client is None:
        sync_redis_client = redis_sync.from_url(settings.REDIS_URL, decode_responses=True)
    return sync_redis_client

class CacheManager:
    """
    Manages Redis cache interactions with a namespaced approach to avoid key conflicts.
    Includes connection pooling for efficiency and sets expiration on cache entries.
    """

    @staticmethod
    def _get_key(key: str) -> str:
        """Prefix keys to avoid conflict with other services."""
        return f"{settings.APP_NAMESPACE}:{key}"

    @staticmethod
    async def get(key: str):
        """Fetches a value from Redis cache by key."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = await get_redis_client()
            value = await client.get(namespaced_key)
            if value:
                logger.info(f"Cache hit for key: {namespaced_key}")
            else:
                logger.info(f"Cache miss for key: {namespaced_key}")
            return value
        except Exception as e:
            logger.error(f"Error fetching from Redis: {e}")
            return None

    @staticmethod
    async def set(key: str, value: str, expire: int = 3600):  # 1 hour default expiration
        """Sets a value in the Redis cache with an optional expiration time."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = await get_redis_client()
            await client.set(namespaced_key, value, ex=expire)
            logger.info(f"Set cache for key: {namespaced_key} with expiration: {expire} seconds")
        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {e}")

    @staticmethod
    def get_sync(key: str):
        """Synchronous version of get for use in Celery tasks."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = get_sync_redis_client()
            value = client.get(namespaced_key)
            if value:
                logger.info(f"Sync cache hit for key: {namespaced_key}")
            else:
                logger.info(f"Sync cache miss for key: {namespaced_key}")
            return value
        except Exception as e:
            logger.error(f"Error fetching from sync Redis: {e}")
            return None

    @staticmethod
    def set_sync(key: str, value: str, expire: int = 3600):
        """Synchronous version of set for use in Celery tasks."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = get_sync_redis_client()
            client.set(namespaced_key, value, ex=expire)
            logger.info(f"Set sync cache for key: {namespaced_key} with expiration: {expire} seconds")
        except Exception as e:
            logger.error(f"Error setting sync Redis key {key}: {e}")

    @staticmethod
    def deserialize(value: str):
        """Deserialize a JSON string from Redis into a Python object."""
        try:
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error deserializing Redis value: {e}")
            return None
