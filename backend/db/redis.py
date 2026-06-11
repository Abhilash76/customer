import json
import logging
from typing import Optional, Any
import redis.asyncio as aioredis
from config import settings

logger = logging.getLogger("backend.db.redis")

class RedisManager:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None

    async def connect(self):
        """Initialize Redis connection."""
        try:
            self.client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await self.client.ping()
            logger.info("Redis connected successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    async def close(self):
        """Close Redis client connection."""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed.")

    async def get_cache(self, key: str) -> Optional[Any]:
        """Get a parsed JSON value from cache."""
        if not self.client:
            return None
        try:
            val = await self.client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Redis get error for key '{key}': {e}")
        return None

    async def set_cache(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set a value in the cache with JSON serialization and TTL (in seconds)."""
        if not self.client:
            return False
        try:
            val_str = json.dumps(value)
            await self.client.setex(key, ttl, val_str)
            return True
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            return False

    async def delete_cache(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.client:
            return False
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            return False

redis_cache = RedisManager()
