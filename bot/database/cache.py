import redis.asyncio as redis
import redis as redis_sync
import logging
import json
import asyncio
from .cache_config import REDIS_URL, APP_NAMESPACE, REDIS_POOL_CONFIG

logger = logging.getLogger(__name__)

# Mapping of asyncio event loops to Redis clients
_redis_clients = {}
# Synchronous Redis client
sync_redis_client = None

async def get_redis_client():
    """Returns the Redis client for the current event loop, initializing it if necessary."""
    loop = asyncio.get_running_loop()
    client = _redis_clients.get(loop)
    if client is None:
        client = await redis.from_url(REDIS_URL, **REDIS_POOL_CONFIG)
        _redis_clients[loop] = client
    return client

def get_sync_redis_client():
    """Returns a synchronous Redis client"""
    global sync_redis_client
    if sync_redis_client is None:
        sync_redis_client = redis_sync.from_url(REDIS_URL, decode_responses=True)
    return sync_redis_client

class CacheManager:
    """
    Manages Redis cache interactions with a namespaced approach to avoid key conflicts.
    Includes connection pooling for efficiency and sets expiration on cache entries.
    """

    @staticmethod
    def _get_key(key: str) -> str:
        """Prefix keys to avoid conflict with other services."""
        return f"{APP_NAMESPACE}:{key}"

    @staticmethod
    async def get(key: str):
        """Fetches a value from Redis cache by key."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = await get_redis_client()
            value = await client.get(namespaced_key)
            logger.debug(f"Cache {'hit' if value else 'miss'} for key: {namespaced_key}")
            return value
        except Exception as e:
            logger.warning(f"Redis GET error for key {key}: {e}")
            return None

    @staticmethod
    async def set(key: str, value: str, expire: int = 3600):  # 1 hour default expiration
        """Sets a value in the Redis cache with an optional expiration time."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = await get_redis_client()
            await client.set(namespaced_key, value, ex=expire)
            logger.debug(f"Set cache for key: {namespaced_key}")
        except Exception as e:
            logger.warning(f"Redis SET error for key {key}: {e}")

    @staticmethod
    async def delete(key: str):
        """Deletes a value from the Redis cache."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = await get_redis_client()
            await client.delete(namespaced_key)
            logger.debug(f"Deleted cache for key: {namespaced_key}")
        except Exception as e:
            logger.warning(f"Redis DELETE error for key {key}: {e}")

    @staticmethod
    async def exists(key: str) -> bool:
        """Checks if a key exists in the Redis cache."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = await get_redis_client()
            exists = await client.exists(namespaced_key)
            return bool(exists)
        except Exception as e:
            logger.error(f"Error checking if Redis key {key} exists: {e}")
            return False

    @staticmethod
    def get_sync(key: str):
        """Synchronous version of get for use in non-async contexts."""
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
        """Synchronous version of set for use in non-async contexts."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = get_sync_redis_client()
            client.set(namespaced_key, value, ex=expire)
            logger.info(f"Set sync cache for key: {namespaced_key} with expiration: {expire} seconds")
        except Exception as e:
            logger.error(f"Error setting sync Redis key {key}: {e}")

    @staticmethod
    def delete_sync(key: str):
        """Synchronous version of delete."""
        try:
            namespaced_key = CacheManager._get_key(key)
            client = get_sync_redis_client()
            client.delete(namespaced_key)
            logger.info(f"Deleted sync cache for key: {namespaced_key}")
        except Exception as e:
            logger.error(f"Error deleting sync Redis key {key}: {e}")

    @staticmethod
    def serialize(data):
        """Serialize a Python object into a JSON string for Redis."""
        try:
            return json.dumps(data)
        except Exception as e:
            logger.error(f"Error serializing data for Redis: {e}")
            return None

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
