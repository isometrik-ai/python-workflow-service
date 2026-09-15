"""Tests for assets."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

ASSETS_BASE = "/api/v1/assets"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def asset_record(**overrides) -> dict:
    """Build a sample asset record for assertions."""
    payload = {
        "id": "asset_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Chiller Unit 1",
        "code": "CH-001",
        "make": "Carrier",
        "model": "30XA",
        "serial_number": "SN-12345",
        "description": "Main chiller",
        "category_id": "asset_category_abc123",
        "status": "operational",
        "location_id": None,
        "location_text": "Roof",
        "landmark_note": None,
        "photos": [],
        "associated_parts": [],
        "purchase_date": date(2024, 1, 15),
        "purchase_cost": 5000000,
        "currency": "INR",
        "supplier": None,
        "supplier_vendor_id": None,
        "purchase_order_number": None,
        "invoice_ref": None,
        "install_date": None,
        "warranty_start": None,
        "warranty_expiry": None,
        "warranty_terms": None,
        "documents": [],
        "custom_field_values": {},
        "contract_id": None,
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def create_asset_payload(**overrides) -> dict:
    """Build a request payload for create asset."""
    payload = {
        "name": "Chiller Unit 1",
        "code": "CH-001",
        "category_id": "asset_category_abc123",
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.assets.AssetService")
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


def test_list_assets_success(client):
    """Test list assets success."""
    patcher, service = setup_service_mock(list=([asset_record()], 1))
    try:
        response = client.get(ASSETS_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == 1
    assert body["data"][0]["code"] == "CH-001"
    service.list.assert_awaited_once()


def test_get_asset_success(client):
    """Test get asset success."""
    patcher, service = setup_service_mock(get=asset_record())
    try:
        response = client.get(f"{ASSETS_BASE}/asset_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["category_id"] == "asset_category_abc123"
    service.get.assert_awaited_once_with("asset_abc123")


def test_get_asset_not_found(client):
    """Test get asset not found."""
    patcher, service = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{ASSETS_BASE}/missing")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get.assert_awaited_once()


def test_create_asset_success(client):
    """Test create asset success."""
    patcher, service = setup_service_mock(create=asset_record())
    try:
        response = client.post(ASSETS_BASE, json=create_asset_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["data"]["name"] == "Chiller Unit 1"
    service.create.assert_awaited_once()


def test_create_asset_duplicate_code(client):
    """Test create asset duplicate code."""
    patcher, service = setup_service_mock(
        create=DuplicateValueException(message_key="assets.errors.duplicate_code")
    )
    try:
        response = client.post(ASSETS_BASE, json=create_asset_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_409_CONFLICT
    service.create.assert_awaited_once()


def test_update_asset_success(client):
    """Test update asset success."""
    updated = asset_record(name="Chiller Unit 2")
    patcher, service = setup_service_mock(update=updated)
    try:
        response = client.patch(
            f"{ASSETS_BASE}/asset_abc123",
            json={"name": "Chiller Unit 2"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["name"] == "Chiller Unit 2"
    service.update.assert_awaited_once()


def test_delete_asset_success(client):
    """Test delete asset success."""
    patcher, service = setup_service_mock(delete="asset_abc123")
    try:
        response = client.delete(f"{ASSETS_BASE}/asset_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "asset_abc123"
    service.delete.assert_awaited_once_with("asset_abc123")
