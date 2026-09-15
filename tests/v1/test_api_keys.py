"""Tests for api keys."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.core.security.internal_auth import require_internal_token
from app.schemas.common import ApiKeyScope

API_KEYS_BASE = "/api/v1/api-keys"


class AttrDict(dict):
    """Dictionary with attribute access."""

    def __init__(self, **kwargs):
        """Initialize attribute-accessible mapping from keyword arguments."""
        super().__init__(**kwargs)
        self.__dict__ = self


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def api_key_record(**overrides) -> dict:
    """Build a sample api key record for assertions."""
    payload = {
        "id": "key-1",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Integration Key",
        "key_prefix": "abc123def456",
        "last_used_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def create_api_key_payload(**overrides) -> dict:
    """Build a request payload for create api key."""
    payload = {
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Integration Key",
    }
    payload.update(overrides)
    return payload


def api_key_created_record(**overrides) -> dict:
    """Build a sample api key created record for assertions."""
    record = api_key_record(**overrides)
    record["key"] = "raw-secret-key-value-shown-once"
    return record


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.api_keys.ApiKeyService")
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


def test_get_project_api_key_success(client):
    """Test get project api key success."""
    patcher, service = setup_service_mock(get_project_api_key=api_key_record())
    try:
        response = client.get(
            API_KEYS_BASE,
            headers={
                "x-api-key": "valid-api-key-value-123456",
                "x-tenant-id": "tenant123",
                "x-project-id": "project123",
            },
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["id"] == "key-1"
    assert body["data"]["tenant_id"] == "tenant123"
    service.get_project_api_key.assert_awaited_once()


def test_get_project_api_key_not_found(client):
    """Test get project api key not found."""
    patcher, service = setup_service_mock(
        get_project_api_key=NotFoundException(message_key="errors.not_found")
    )
    try:
        response = client.get(API_KEYS_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get_project_api_key.assert_awaited_once()


def test_create_api_key_success(client):
    """Test create api key success."""
    patcher, service = setup_service_mock(create_api_key=api_key_created_record())
    overrides = client.app.dependency_overrides.copy()
    client.app.dependency_overrides[require_internal_token] = lambda: None
    try:
        response = client.post(
            API_KEYS_BASE,
            json=create_api_key_payload(),
            headers={"x-internal-token": "change-me-internal-token"},
        )
    finally:
        patcher.stop()
        client.app.dependency_overrides.clear()
        client.app.dependency_overrides.update(overrides)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["id"] == "key-1"
    assert body["data"]["key"] == "raw-secret-key-value-shown-once"
    service.create_api_key.assert_awaited_once_with(
        tenant_id="tenant123",
        project_id="project123",
        name="Integration Key",
    )


def test_create_api_key_conflict(client):
    """Test create api key conflict."""
    patcher, service = setup_service_mock(
        create_api_key=DuplicateValueException(message_key="api_keys.errors.already_exists")
    )
    overrides = client.app.dependency_overrides.copy()
    client.app.dependency_overrides[require_internal_token] = lambda: None
    try:
        response = client.post(API_KEYS_BASE, json=create_api_key_payload())
    finally:
        patcher.stop()
        client.app.dependency_overrides.clear()
        client.app.dependency_overrides.update(overrides)

    assert response.status_code == status.HTTP_409_CONFLICT
    service.create_api_key.assert_awaited_once()


def test_revoke_api_key_success(client):
    """Test revoke api key success."""
    patcher, service = setup_service_mock(revoke_api_key="key-1")
    try:
        response = client.delete(f"{API_KEYS_BASE}/key-1")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["id"] == "key-1"
    service.revoke_api_key.assert_awaited_once_with("key-1")


def test_revoke_api_key_not_found(client):
    """Test revoke api key not found."""
    patcher, service = setup_service_mock(
        revoke_api_key=NotFoundException(message_key="errors.not_found")
    )
    try:
        response = client.delete(f"{API_KEYS_BASE}/missing-key")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.revoke_api_key.assert_awaited_once_with("missing-key")
