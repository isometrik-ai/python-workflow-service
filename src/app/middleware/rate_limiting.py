"""Rate limiting middleware components for the FastAPI application."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config.app_config import EnvironmentOption, settings
from app.core.utils.logger import logger


def get_limiter():
    """Create and configure the rate limiter with Redis backend."""
    try:
        # Use in-memory storage for tests
        if settings.ENVIRONMENT == EnvironmentOption.TEST:
            logger.info("🔄 Using in-memory rate limiting for tests")
            limiter = Limiter(
                key_func=get_remote_address,
                strategy="fixed-window",
                default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
                headers_enabled=True,
            )
            return limiter

        storage_uri = (
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_RATE_LIMIT_DB}"
        )

        # If Redis auth is configured, add it to the URI
        if settings.REDIS_PASSWORD:
            auth_part = f"{settings.REDIS_USERNAME}:{settings.REDIS_PASSWORD}@"
            storage_uri = (
                f"redis://{auth_part}"
                f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/"
                f"{settings.REDIS_RATE_LIMIT_DB}"
            )

        # Create limiter with Redis backend and IP-based rate limiting
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=storage_uri,
            strategy="fixed-window",  # or "moving-window" for more accuracy
            default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
            headers_enabled=True,
        )

        logger.info("✅ Rate limiter configured with Redis backend")
        return limiter

    except Exception as e:
        logger.error("❌ Failed to configure rate limiter with Redis: %s", e)
        # Fallback to in-memory storage if Redis is not available
        logger.warning("⚠️ Falling back to in-memory rate limiting (not suitable for production)")

        limiter = Limiter(
            key_func=get_remote_address,
            strategy="fixed-window",
            default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
            headers_enabled=True,
        )

        logger.info("✅ Rate limiter configured with in-memory backend")
        return limiter


# Global limiter instance
limiter = get_limiter()
