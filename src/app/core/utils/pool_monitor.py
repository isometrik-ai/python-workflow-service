"""Connection pool monitoring utilities."""

import time
from dataclasses import dataclass
from typing import Any

from app.core.utils.logger import logger


@dataclass
class PoolMetrics:
    """Connection pool metrics data class."""

    total_connections: int
    active_connections: int
    idle_connections: int
    connection_errors: int
    last_check: float
    pool_name: str


class PoolMonitor:
    """Monitor for connection pool metrics."""

    def __init__(self):
        """Initialize empty metrics and error counters."""
        self.metrics: dict[str, PoolMetrics] = {}
        self.error_counts: dict[str, int] = {}

    def update_postgres_metrics(self, engine) -> PoolMetrics | None:
        """Update PostgreSQL connection pool metrics."""
        try:
            pool = engine.pool
            metrics = PoolMetrics(
                total_connections=pool.size(),
                active_connections=pool.checkedin() + pool.checkedout(),
                idle_connections=pool.checkedin(),
                connection_errors=self.error_counts.get("postgres", 0),
                last_check=time.time(),
                pool_name="postgres",
            )
            self.metrics["postgres"] = metrics
            return metrics
        except Exception as e:
            logger.error("Failed to update PostgreSQL metrics: %s", e)
            return None

    def update_redis_metrics(self, pool) -> PoolMetrics | None:
        """Update Redis connection pool metrics."""
        try:
            metrics = PoolMetrics(
                total_connections=pool._created_connections,
                active_connections=pool._created_connections - pool._available_connections,
                idle_connections=pool._available_connections,
                connection_errors=self.error_counts.get("redis", 0),
                last_check=time.time(),
                pool_name="redis",
            )
            self.metrics["redis"] = metrics
            return metrics
        except Exception as e:
            logger.error("Failed to update Redis metrics: %s", e)
            return None

    def increment_error_count(self, pool_name: str) -> None:
        """Increment error count for a specific pool."""
        self.error_counts[pool_name] = self.error_counts.get(pool_name, 0) + 1

    def get_metrics(self) -> dict[str, PoolMetrics]:
        """Get all current metrics."""
        return self.metrics.copy()

    def get_pool_health(self, pool_name: str) -> dict[str, Any]:
        """Get health status for a specific pool."""
        if pool_name not in self.metrics:
            return {"status": "unknown", "error": "No metrics available"}

        metrics = self.metrics[pool_name]
        error_rate = metrics.connection_errors / max(metrics.total_connections, 1)

        if error_rate > 0.1:
            status = "unhealthy"
        elif error_rate > 0.05:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "total_connections": metrics.total_connections,
            "active_connections": metrics.active_connections,
            "idle_connections": metrics.idle_connections,
            "error_count": metrics.connection_errors,
            "error_rate": error_rate,
            "last_check": metrics.last_check,
        }


pool_monitor = PoolMonitor()
