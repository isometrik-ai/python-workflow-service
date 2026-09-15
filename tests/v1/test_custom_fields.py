"""Tests for custom fields."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

CUSTOM_FIELDS_BASE = "/api/v1/custom-fields"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def custom_field_record(**overrides) -> dict:
    """Build a sample custom field record."""
    payload = {
        "id": "custom_field_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "field_name": "Installation Date",
        "field_key": "installation_date",
        "field_type": "date",
        "type_config": {},
        "is_required": False,
        "is_active": True,
        "sort_order": 1,
        "show_on_create": True,
        "show_on_detail": True,
        "scope": "global",
        "category_id": None,
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for CustomFieldService."""
    patcher = patch("app.api.v1.custom_fields.CustomFieldService")
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
    """Override API key scope dependency."""
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


def test_list_custom_fields_success(client):
    """List custom fields returns paginated envelope."""
    patcher, _instance = setup_service_mock(list=([custom_field_record()], 1))
    try:
        response = client.get(CUSTOM_FIELDS_BASE)
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["total"] == 1
        assert body["data"][0]["field_key"] == "installation_date"
    finally:
        patcher.stop()


def test_create_custom_field_success(client):
    """Create custom field returns 201."""
    patcher, _instance = setup_service_mock(create=custom_field_record())
    try:
        response = client.post(
            CUSTOM_FIELDS_BASE,
            json={
                "field_name": "Installation Date",
                "field_key": "installation_date",
                "field_type": "date",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["field_key"] == "installation_date"
    finally:
        patcher.stop()


def test_get_custom_field_not_found(client):
    """Get missing custom field returns 404."""
    patcher, _instance = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{CUSTOM_FIELDS_BASE}/missing")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    finally:
        patcher.stop()
