"""Tests for contracts."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

CONTRACTS_BASE = "/api/v1/contracts"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def contract_record(**overrides) -> dict:
    """Build a sample contract record for assertions."""
    payload = {
        "id": "contract_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "title": "Annual HVAC Maintenance",
        "vendor_id": "vendor_abc123",
        "asset_ids": ["asset_abc123"],
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 12, 31),
        "visit_frequency": "quarterly",
        "payment_frequency": "quarterly",
        "value": 100000,
        "currency": "INR",
        "status": "active",
        "next_visit_date": date(2026, 4, 1),
        "last_serviced_date": None,
        "auto_generate_lead_days": 14,
        "scope_included": "Quarterly inspection",
        "scope_excluded": None,
        "form_template_id": None,
        "pre_start_form_template_id": None,
        "documents": [],
        "termination_reason": None,
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def create_contract_payload(**overrides) -> dict:
    """Build a request payload for create contract."""
    payload = {
        "title": "Annual HVAC Maintenance",
        "vendor_id": "vendor_abc123",
        "start_date": "2026-01-01",
        "asset_ids": ["asset_abc123"],
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.contracts.ContractService")
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


def test_list_contracts_success(client):
    """Test list contracts success."""
    patcher, service = setup_service_mock(list=([contract_record()], 1))
    try:
        response = client.get(CONTRACTS_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == 1
    assert body["data"][0]["title"] == "Annual HVAC Maintenance"
    service.list.assert_awaited_once()


def test_get_contract_success(client):
    """Test get contract success."""
    patcher, service = setup_service_mock(get=contract_record())
    try:
        response = client.get(f"{CONTRACTS_BASE}/contract_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["vendor_id"] == "vendor_abc123"
    service.get.assert_awaited_once_with("contract_abc123")


def test_get_contract_not_found(client):
    """Test get contract not found."""
    patcher, service = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{CONTRACTS_BASE}/missing")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get.assert_awaited_once()


def test_create_contract_success(client):
    """Test create contract success."""
    patcher, service = setup_service_mock(create=contract_record())
    try:
        response = client.post(CONTRACTS_BASE, json=create_contract_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["data"]["status"] == "active"
    service.create.assert_awaited_once()


def test_update_contract_success(client):
    """Test update contract success."""
    updated = contract_record(title="Updated Contract")
    patcher, service = setup_service_mock(update=updated)
    try:
        response = client.patch(
            f"{CONTRACTS_BASE}/contract_abc123",
            json={"title": "Updated Contract"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["title"] == "Updated Contract"
    service.update.assert_awaited_once()


def test_delete_contract_success(client):
    """Test delete contract success."""
    patcher, service = setup_service_mock(delete="contract_abc123")
    try:
        response = client.delete(f"{CONTRACTS_BASE}/contract_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "contract_abc123"
    service.delete.assert_awaited_once_with("contract_abc123")
