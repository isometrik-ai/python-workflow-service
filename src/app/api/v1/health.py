"""Health and metrics endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import text

from app.core.config.app_config import settings
from app.core.db.postgres.database import async_engine, async_session_maker
from app.core.db.redis import redis
from app.core.utils.logger import logger
from app.core.utils.pool_monitor import pool_monitor
from app.schemas.health import HealthCheckResponse

router = APIRouter(tags=["Health"])


async def check_database_health() -> bool:
    """Check if the database is healthy by running a simple query."""
    try:
        # First, test the connection pool directly
        async with async_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()

        # Also test with a session to ensure session management works
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()

        return True
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False


async def check_redis_health() -> bool:
    """Check if Redis is healthy."""
    if redis is None:
        return False
    try:
        return await redis.health_check()
    except Exception as e:
        logger.error("Redis health check failed: %s", e)
        return False


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    include_db: bool = Query(False, description="Include database health check"),
    include_cache: bool = Query(False, description="Include cache health check"),
) -> HealthCheckResponse:
    """Health check endpoint that verifies the status of all services.

    Parameters
    ----------
    include_db : bool
        Whether to include database health check
    include_cache : bool
        Whether to include cache health check

    Returns:
    -------
    HealthCheckResponse
        Health status of all services

    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": settings.APP_VERSION or "1.0.0",
        "environment": settings.ENVIRONMENT.value,
        "services": {},
    }

    # Check database health
    if include_db:
        db_healthy = await check_database_health()
        health_status["services"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "type": "postgresql",
        }
        if not db_healthy:
            health_status["status"] = "degraded"

    # Check Redis cache health
    if include_cache:
        redis_healthy = await check_redis_health()
        health_status["services"]["cache"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "type": "redis",
        }
        if not redis_healthy:
            health_status["status"] = "degraded"

    return HealthCheckResponse(**health_status)


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Get connection pool metrics for all databases.

    Returns:
    -------
    dict
        Connection pool metrics for all databases

    """
    try:
        # Update PostgreSQL metrics
        if hasattr(async_engine, "pool"):
            pool_monitor.update_postgres_metrics(async_engine)

        # Update Redis metrics
        if hasattr(redis, "_pool") and redis is not None and redis._pool:
            pool_monitor.update_redis_metrics(redis._pool)

        # Get all metrics
        metrics = pool_monitor.get_metrics()

        # Convert to serializable format
        result = {"timestamp": datetime.now(UTC).isoformat(), "pools": {}}

        for pool_name, pool_metrics in metrics.items():
            result["pools"][pool_name] = {
                "total_connections": pool_metrics.total_connections,
                "active_connections": pool_metrics.active_connections,
                "idle_connections": pool_metrics.idle_connections,
                "connection_errors": pool_metrics.connection_errors,
                "last_check": pool_metrics.last_check,
                "health": pool_monitor.get_pool_health(pool_name),
            }

        return result

    except Exception as e:
        return {
            "error": f"Failed to get metrics: {str(e)}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
