"""Tests for scheduler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.internal_auth import get_scheduler_auth
from app.schemas.common import ApiKeyScope

SCHEDULER_BASE = "/api/v1/scheduler/run"


@pytest.fixture(scope="function", autouse=True)
def override_scheduler_auth(client):
    """Override dependencies for scheduler auth during tests."""
    scope = ApiKeyScope(
        tenant_id="tenant123",
        project_id="project123",
        api_key_id="key-1",
        api_key_name="Integration Key",
    )
    overrides = client.app.dependency_overrides.copy()
    client.app.dependency_overrides[get_scheduler_auth] = lambda: scope
    yield
    client.app.dependency_overrides.clear()
    client.app.dependency_overrides.update(overrides)


def test_run_scheduler_success(client):
    """Test run scheduler success."""
    patcher = patch("app.api.v1.scheduler.SchedulerService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.run_once = AsyncMock(return_value={"created": 2, "cancelled": 0, "skipped": 1})
    service_cls.return_value = instance
    try:
        response = client.post(SCHEDULER_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["created"] == 2
    assert body["data"]["skipped"] == 1
    instance.run_once.assert_awaited_once_with("tenant123")


def test_run_scheduler_locked(client):
    """Test run scheduler locked."""
    patcher = patch("app.api.v1.scheduler.SchedulerService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.run_once = AsyncMock(
        return_value={"created": 0, "cancelled": 0, "skipped": 0, "locked": 1}
    )
    service_cls.return_value = instance
    try:
        response = client.post(SCHEDULER_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["locked"] == 1
