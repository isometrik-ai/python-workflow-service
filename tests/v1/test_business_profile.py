"""Tests for business profile."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

BUSINESS_PROFILE_BASE = "/api/v1/business-profile"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def business_profile_record(**overrides) -> dict:
    """Build a sample business profile record."""
    payload = {
        "id": "default",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Acme FM",
        "legal_name": "Acme Facilities Pvt Ltd",
        "gstin": "",
        "address_line": "",
        "city": "",
        "state": "",
        "pincode": "",
        "phone": "",
        "email": "",
        "website": "",
        "logo": {},
        "bank_name": "",
        "bank_account": "",
        "bank_ifsc": "",
        "default_wo_notes": "",
        "default_wo_terms": "",
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


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


def test_get_business_profile_success(client):
    """GET business profile returns singleton row."""
    patcher = patch("app.api.v1.business_profile.BusinessProfileService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.get = AsyncMock(return_value=business_profile_record())
    service_cls.return_value = instance
    try:
        response = client.get(BUSINESS_PROFILE_BASE)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["name"] == "Acme FM"
    finally:
        patcher.stop()


def test_put_business_profile_success(client):
    """PUT business profile upserts fields."""
    patcher = patch("app.api.v1.business_profile.BusinessProfileService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.upsert = AsyncMock(return_value=business_profile_record(name="Updated FM"))
    service_cls.return_value = instance
    try:
        response = client.put(BUSINESS_PROFILE_BASE, json={"name": "Updated FM"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["name"] == "Updated FM"
    finally:
        patcher.stop()
