"""Tests for health."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status


def assert_iso_timestamp(value: str) -> None:
    """Validate ISO-8601 timestamp string (with optional trailing Z)."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Invalid ISO timestamp: {value}")


def test_health_check_default(client):
    """Test health check default."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "healthy"
    assert_iso_timestamp(body["timestamp"])
    assert isinstance(body["version"], str)
    assert isinstance(body["environment"], str)
    assert body["services"] == {}


def test_health_check_with_all_services_success(client):
    """Test health check with all services success."""
    with (
        patch("app.api.v1.health.check_database_health", new_callable=AsyncMock) as mock_db,
        patch("app.api.v1.health.check_redis_health", new_callable=AsyncMock) as mock_cache,
    ):
        mock_db.return_value = True
        mock_cache.return_value = True

        response = client.get(
            "/api/v1/health",
            params={"include_db": "true", "include_cache": "true"},
        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "healthy"
    assert body["services"]["database"]["status"] == "healthy"
    assert body["services"]["cache"]["status"] == "healthy"
    mock_db.assert_awaited_once()
    mock_cache.assert_awaited_once()


def test_health_check_db_failure(client):
    """Test health check db failure."""
    with patch("app.api.v1.health.check_database_health", new_callable=AsyncMock) as mock_db:
        mock_db.return_value = False
        response = client.get("/api/v1/health", params={"include_db": "true"})

    body = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert body["status"] == "degraded"
    assert body["services"]["database"]["status"] == "unhealthy"
    mock_db.assert_awaited_once()


def test_health_check_cache_failure(client):
    """Test health check cache failure."""
    with patch("app.api.v1.health.check_redis_health", new_callable=AsyncMock) as mock_cache:
        mock_cache.return_value = False
        response = client.get("/api/v1/health", params={"include_cache": "true"})

    body = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert body["status"] == "degraded"
    assert body["services"]["cache"]["status"] == "unhealthy"
    mock_cache.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_database_health_success(monkeypatch):
    """Test check database health success."""
    mock_engine = MagicMock()
    engine_cm = AsyncMock()
    conn = MagicMock()
    result = MagicMock()
    result.scalar.return_value = 1
    conn.execute = AsyncMock(return_value=result)
    engine_cm.__aenter__.return_value = conn
    mock_engine.begin.return_value = engine_cm

    mock_session_factory = MagicMock()
    session_cm = AsyncMock()
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session_cm.__aenter__.return_value = session
    mock_session_factory.return_value = session_cm

    monkeypatch.setattr("app.api.v1.health.async_engine", mock_engine)
    monkeypatch.setattr("app.api.v1.health.async_session_maker", mock_session_factory)

    from app.api.v1.health import check_database_health

    assert await check_database_health() is True
    conn.execute.assert_called_once()
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_database_health_failure(monkeypatch):
    """Test check database health failure."""
    mock_engine = MagicMock()
    engine_cm = AsyncMock()
    engine_cm.__aenter__.side_effect = Exception("boom")
    mock_engine.begin.return_value = engine_cm
    monkeypatch.setattr("app.api.v1.health.async_engine", mock_engine)
    monkeypatch.setattr("app.api.v1.health.async_session_maker", MagicMock())

    from app.api.v1.health import check_database_health

    assert await check_database_health() is False


@pytest.mark.asyncio
async def test_check_redis_health_success(monkeypatch):
    """Test check redis health success."""
    redis_mock = MagicMock()
    redis_mock.health_check = AsyncMock(return_value=True)
    monkeypatch.setattr("app.api.v1.health.redis", redis_mock)

    from app.api.v1.health import check_redis_health

    assert await check_redis_health() is True
    redis_mock.health_check.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_redis_health_failure(monkeypatch):
    """Test check redis health failure."""
    redis_mock = MagicMock()
    redis_mock.health_check = AsyncMock(side_effect=Exception("down"))
    monkeypatch.setattr("app.api.v1.health.redis", redis_mock)

    from app.api.v1.health import check_redis_health

    assert await check_redis_health() is False
    redis_mock.health_check.assert_awaited_once()


def test_get_metrics_success(client):
    """Test get metrics success."""
    pool_metrics = MagicMock(
        total_connections=10,
        active_connections=4,
        idle_connections=6,
        connection_errors=0,
        last_check=123.0,
    )

    with (
        patch("app.api.v1.health.pool_monitor") as mock_pool_monitor,
        patch("app.api.v1.health.async_engine") as mock_engine,
        patch("app.api.v1.health.redis") as mock_redis,
    ):
        mock_engine.pool = MagicMock()
        mock_redis._pool = MagicMock()
        mock_pool_monitor.get_metrics.return_value = {"postgres": pool_metrics}
        mock_pool_monitor.get_pool_health.return_value = {"status": "healthy"}

        response = client.get("/api/v1/metrics")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert_iso_timestamp(body["timestamp"])
    postgres = body["pools"]["postgres"]
    assert postgres["total_connections"] == 10
    assert postgres["active_connections"] == 4
    assert postgres["idle_connections"] == 6
    assert postgres["connection_errors"] == 0
    assert postgres["last_check"] == 123.0
    assert postgres["health"] == {"status": "healthy"}


def test_get_metrics_failure(client):
    """Test get metrics failure."""
    with patch("app.api.v1.health.pool_monitor") as mock_pool_monitor:
        mock_pool_monitor.update_postgres_metrics.side_effect = Exception("metrics unavailable")
        response = client.get("/api/v1/metrics")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert "Failed to get metrics" in body["error"]
    assert_iso_timestamp(body["timestamp"])
