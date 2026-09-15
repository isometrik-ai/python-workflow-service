"""Tests for asset categories."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

ASSET_CATEGORIES_BASE = "/api/v1/asset-categories"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def asset_category_record(**overrides) -> dict:
    """Build a sample asset category record for assertions."""
    payload = {
        "id": "asset_category_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "HVAC",
        "description": "Heating and cooling",
        "parent_id": None,
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def create_asset_category_payload(**overrides) -> dict:
    """Build a request payload for create asset category."""
    payload = {
        "name": "HVAC",
        "description": "Heating and cooling",
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.asset_categories.AssetCategoryService")
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


def test_list_asset_categories_success(client):
    """Test list asset categories success."""
    patcher, service = setup_service_mock(list=([asset_category_record()], 1))
    try:
        response = client.get(ASSET_CATEGORIES_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == 1
    assert body["data"][0]["id"] == "asset_category_abc123"
    assert body["data"][0]["name"] == "HVAC"
    service.list.assert_awaited_once()


def test_get_asset_category_success(client):
    """Test get asset category success."""
    patcher, service = setup_service_mock(get=asset_category_record())
    try:
        response = client.get(f"{ASSET_CATEGORIES_BASE}/asset_category_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["tenant_id"] == "tenant123"
    service.get.assert_awaited_once_with("asset_category_abc123")


def test_get_asset_category_not_found(client):
    """Test get asset category not found."""
    patcher, service = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{ASSET_CATEGORIES_BASE}/missing")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get.assert_awaited_once()


def test_create_asset_category_success(client):
    """Test create asset category success."""
    patcher, service = setup_service_mock(create=asset_category_record())
    try:
        response = client.post(ASSET_CATEGORIES_BASE, json=create_asset_category_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["data"]["name"] == "HVAC"
    service.create.assert_awaited_once_with(
        name="HVAC",
        description="Heating and cooling",
        parent_id=None,
    )


def test_update_asset_category_success(client):
    """Test update asset category success."""
    updated = asset_category_record(name="HVAC Systems")
    patcher, service = setup_service_mock(update=updated)
    try:
        response = client.patch(
            f"{ASSET_CATEGORIES_BASE}/asset_category_abc123",
            json={"name": "HVAC Systems"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["name"] == "HVAC Systems"
    service.update.assert_awaited_once()


def test_delete_asset_category_success(client):
    """Test delete asset category success."""
    patcher, service = setup_service_mock(delete="asset_category_abc123")
    try:
        response = client.delete(f"{ASSET_CATEGORIES_BASE}/asset_category_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "asset_category_abc123"
    service.delete.assert_awaited_once_with("asset_category_abc123")
