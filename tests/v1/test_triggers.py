"""Tests for triggers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import NotFoundException, ValidationException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

TRIGGERS_BASE = "/api/v1/triggers"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def trigger_record(**overrides) -> dict:
    """Build a sample trigger record for assertions."""
    payload = {
        "id": "trigger_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Work order created",
        "entity": "work_order",
        "event": "created",
        "is_active": True,
        "webhook_url": "https://example.com/webhooks/work-orders",
        "secret": "whsec_test",
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def create_trigger_payload(**overrides) -> dict:
    """Build a request payload for create trigger."""
    payload = {
        "name": "Work order created",
        "entity": "work_order",
        "event": "created",
        "webhook_url": "https://example.com/webhooks/work-orders",
        "secret": "whsec_test",
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.triggers.TriggerService")
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


def test_list_triggers_success(client):
    """Test list triggers success."""
    patcher, service = setup_service_mock(list=[trigger_record()])
    try:
        response = client.get(TRIGGERS_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["items"][0]["name"] == "Work order created"
    service.list.assert_awaited_once()


def test_get_trigger_success(client):
    """Test get trigger success."""
    patcher, service = setup_service_mock(get=trigger_record())
    try:
        response = client.get(f"{TRIGGERS_BASE}/trigger_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["name"] == "Work order created"
    service.get.assert_awaited_once_with("trigger_abc123")


def test_get_trigger_not_found(client):
    """Test get trigger not found."""
    patcher, service = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{TRIGGERS_BASE}/missing")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get.assert_awaited_once()


def test_create_trigger_success(client):
    """Test create trigger success."""
    patcher, service = setup_service_mock(create=trigger_record())
    try:
        response = client.post(TRIGGERS_BASE, json=create_trigger_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    service.create.assert_awaited_once()


def test_create_trigger_invalid_url(client):
    """Test create trigger invalid url."""
    patcher, service = setup_service_mock(
        create=ValidationException(
            message_key="errors.validation",
            params={"message": "Invalid webhook URL"},
        )
    )
    try:
        response = client.post(TRIGGERS_BASE, json=create_trigger_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    service.create.assert_awaited_once()


def test_update_trigger_success(client):
    """Test update trigger success."""
    updated = trigger_record(name="Updated trigger")
    patcher, service = setup_service_mock(update=updated)
    try:
        response = client.patch(
            f"{TRIGGERS_BASE}/trigger_abc123",
            json={"name": "Updated trigger"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["name"] == "Updated trigger"
    service.update.assert_awaited_once()


def test_delete_trigger_success(client):
    """Test delete trigger success."""
    patcher, service = setup_service_mock(delete="trigger_abc123")
    try:
        response = client.delete(f"{TRIGGERS_BASE}/trigger_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "trigger_abc123"
    service.delete.assert_awaited_once_with("trigger_abc123")


def test_test_trigger_success(client):
    """Test test trigger success."""
    patcher, service = setup_service_mock(
        test={"delivered": True, "status": 200, "error": None, "duration_ms": 42}
    )
    try:
        response = client.post(f"{TRIGGERS_BASE}/trigger_abc123/test")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["delivered"] is True
    service.test.assert_awaited_once()


def test_test_trigger_not_found(client):
    """Test test trigger not found."""
    patcher, service = setup_service_mock(test=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.post(f"{TRIGGERS_BASE}/missing/test")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.test.assert_awaited_once()
