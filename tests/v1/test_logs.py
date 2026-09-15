"""Tests for logs."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

AUDIT_EVENTS_BASE = "/api/v1/audit-events"
WEBHOOK_DELIVERIES_BASE = "/api/v1/webhook-deliveries"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def audit_event_record(**overrides) -> dict:
    """Build a sample audit event record for assertions."""
    payload = {
        "id": "audit_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "entity": "work_order",
        "entity_id": "work_order_abc123",
        "entity_label": "Replace filter",
        "action": "created",
        "actor": "Alex",
        "source": "fm",
        "changes": [],
        "snapshot": {"title": "Replace filter"},
        "at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def webhook_delivery_record(**overrides) -> dict:
    """Build a sample webhook delivery record for assertions."""
    payload = {
        "id": "webhook_delivery_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "trigger_id": "trigger_abc123",
        "entity": "work_order",
        "entity_id": "test",
        "event": "work_order.test",
        "request_payload": {"action": "test"},
        "response_status": 200,
        "error": None,
        "attempt": 1,
        "duration_ms": 42,
        "delivered": True,
        "created_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.logs.LogService")
    service_cls = patcher.start()
    instance = MagicMock()
    for method, result in async_methods.items():
        if isinstance(result, Exception):
            async_mock = AsyncMock(side_effect=result)
        else:
            async_mock = AsyncMock(return_value=result)
        setattr(instance, method, async_mock)
    service_cls.return_value = instance
    return patcher, instance


@pytest.fixture(scope="function", autouse=True)
def override_dependencies(client):
    """Override dependencies for dependencies during tests."""
    scope = ApiKeyScope(
        tenant_id="tenant123",
        project_id="project123",
        api_key_id="key-1",
        api_key_name="Integration Key",
    )
    overrides = client.app.dependency_overrides.copy()
    client.app.dependency_overrides[get_api_key_scope] = lambda: scope
    yield
    client.app.dependency_overrides.clear()
    client.app.dependency_overrides.update(overrides)


def test_list_audit_events_success(client):
    """Test list audit events success."""
    patcher, service = setup_service_mock(list_audit_events=([audit_event_record()], 1))
    try:
        response = client.get(AUDIT_EVENTS_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total"] == 1
    assert body["data"][0]["action"] == "created"
    service.list_audit_events.assert_awaited_once()


def test_list_webhook_deliveries_success(client):
    """Test list webhook deliveries success."""
    patcher, service = setup_service_mock(list_webhook_deliveries=([webhook_delivery_record()], 1))
    try:
        response = client.get(WEBHOOK_DELIVERIES_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total"] == 1
    assert body["data"][0]["delivered"] is True
    service.list_webhook_deliveries.assert_awaited_once()
