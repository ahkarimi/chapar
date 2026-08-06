from fastapi import HTTPException
from app.core.cache import CacheManager

class RateLimiter:
    def __init__(self, cache: CacheManager):
        self.cache = cache

    async def check_rate_limit(self, user_id: int, limit: int, window: int = 3600):
        key = f"rate_limit:{user_id}"
        current = await self.cache.get(key)

        if current is None:
            await self.cache.set(key, "1", window)
            return True

        if int(current) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        await self.cache.set(key, str(int(current) + 1), window)
        return True
