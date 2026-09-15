"""Tests for vendors (HoA integration with mocked fallback)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

VENDORS_BASE = "/api/v1/vendors"


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


def test_list_vendors_success(client):
    """List vendors returns merged HoA/local data."""
    patcher = patch("app.api.v1.vendors.VendorService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.list = AsyncMock(
        return_value={
            "total": 1,
            "data": [{"id": "ven-1", "name": "Blue Star HVAC Services", "source": "local"}],
        }
    )
    service_cls.return_value = instance
    try:
        response = client.get(VENDORS_BASE)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["total"] == 1
    finally:
        patcher.stop()


def test_search_vendors_success(client):
    """Search vendors returns filtered results."""
    patcher = patch("app.api.v1.vendors.VendorService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.search = AsyncMock(
        return_value={
            "total": 1,
            "data": [{"id": "ven-1", "name": "Blue Star HVAC Services", "source": "local"}],
        }
    )
    service_cls.return_value = instance
    try:
        response = client.get(f"{VENDORS_BASE}/search", params={"q": "Blue"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["data"][0]["name"].startswith("Blue")
    finally:
        patcher.stop()


def test_create_vendor_success(client):
    """Create vendor returns 201."""
    patcher = patch("app.api.v1.vendors.VendorService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.create = AsyncMock(
        return_value={"id": "ven-new", "name": "New Vendor", "source": "local"}
    )
    service_cls.return_value = instance
    try:
        response = client.post(VENDORS_BASE, json={"name": "New Vendor"})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["name"] == "New Vendor"
    finally:
        patcher.stop()
