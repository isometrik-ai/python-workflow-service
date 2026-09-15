"""Async Redis client with connection pooling."""

import asyncio

from redis.asyncio import ConnectionPool, Redis

from app.core.config.app_config import settings
from app.core.utils.logger import logger


class RedisService:
    """Redis service with connection pooling and async support."""

    def __init__(self, redis_url: str):
        """Initialize the Redis service with the given connection URL."""
        self.redis_url = redis_url
        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> Redis:
        """Get or create Redis client with connection pooling and retry logic."""
        if self._client is not None:
            return self._client

        async with self._lock:
            if self._client is not None:
                return self._client

            max_retries = settings.REDIS_MAX_RETRIES
            retry_delay = settings.REDIS_RETRY_DELAY

            for attempt in range(max_retries):
                try:
                    self._pool = ConnectionPool.from_url(
                        self.redis_url,
                        max_connections=settings.REDIS_MAX_CONNECTIONS,
                        retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                        socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                        decode_responses=True,
                    )
                    self._client = Redis(connection_pool=self._pool)

                    # Test connection
                    await self._client.ping()
                    logger.info("✅ Redis connected successfully")
                    break

                except Exception as e:
                    logger.warning("Redis connection attempt %s failed: %s", attempt + 1, e)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2**attempt))  # Exponential backoff
                    else:
                        logger.error("Redis not available after all retries: %s", e)
                        self._client = None
                        raise

        return self._client

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy."""
        try:
            client = await self.get_client()
            if client is None:
                return False
            await client.ping()
            return True
        except Exception:
            return False

    async def close(self):
        """Close Redis connection."""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            logger.info("✅ Redis connection closed")

            if self._pool:
                await self._pool.disconnect()
                self._pool = None

        except Exception as e:
            logger.error("Error closing Redis: %s", e)


def create_redis() -> RedisService:
    """Create Redis service instance."""
    return RedisService(settings.redis_url)


# Create global redis instance
try:
    redis = create_redis()
except Exception as e:
    logger.warning("Failed to initialize Redis: %s", e)
    redis = None
