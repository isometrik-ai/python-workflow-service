"""Tests for invoices."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

INVOICES_BASE = "/api/v1/invoices"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def invoice_record(**overrides) -> dict:
    """Build a sample invoice record for assertions."""
    payload = {
        "id": "invoice_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "work_order_id": "work_order_abc123",
        "vendor_id": "vendor_abc123",
        "invoice_number": "INV-2026-001",
        "date": date(2026, 4, 1),
        "line_items": [{"description": "Labor", "amount": 50000}],
        "subtotal": 50000,
        "tax": 9000,
        "total": 59000,
        "currency": "INR",
        "status": "submitted",
        "document": {},
        "files": [],
        "timeline": [{"id": "evt-1", "type": "submitted", "at": iso_timestamp()}],
        "revisions": [],
        "payment_id": None,
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def create_invoice_payload(**overrides) -> dict:
    """Build a request payload for create invoice."""
    payload = {
        "work_order_id": "work_order_abc123",
        "vendor_id": "vendor_abc123",
        "invoice_number": "INV-2026-001",
        "subtotal": 50000,
        "tax": 9000,
        "total": 59000,
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.invoices.InvoiceService")
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


def test_list_invoices_success(client):
    """Test list invoices success."""
    patcher, service = setup_service_mock(list=([invoice_record()], 1))
    try:
        response = client.get(INVOICES_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == 1
    assert body["data"][0]["invoice_number"] == "INV-2026-001"
    service.list.assert_awaited_once()


def test_get_invoice_success(client):
    """Test get invoice success."""
    patcher, service = setup_service_mock(get=invoice_record())
    try:
        response = client.get(f"{INVOICES_BASE}/invoice_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["status"] == "submitted"
    service.get.assert_awaited_once_with("invoice_abc123")


def test_get_invoice_not_found(client):
    """Test get invoice not found."""
    patcher, service = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{INVOICES_BASE}/missing")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get.assert_awaited_once()


def test_create_invoice_success(client):
    """Test create invoice success."""
    patcher, service = setup_service_mock(create=invoice_record())
    try:
        response = client.post(INVOICES_BASE, json=create_invoice_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["data"]["total"] == 59000
    service.create.assert_awaited_once()


def test_create_invoice_duplicate_number(client):
    """Test create invoice duplicate number."""
    patcher, service = setup_service_mock(
        create=DuplicateValueException(message_key="invoices.errors.duplicate_number")
    )
    try:
        response = client.post(INVOICES_BASE, json=create_invoice_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_409_CONFLICT
    service.create.assert_awaited_once()


def test_update_invoice_success(client):
    """Test update invoice success."""
    updated = invoice_record(status="approved")
    patcher, service = setup_service_mock(update=updated)
    try:
        response = client.patch(
            f"{INVOICES_BASE}/invoice_abc123",
            json={"status": "approved"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["status"] == "approved"
    service.update.assert_awaited_once()


def test_delete_invoice_success(client):
    """Test delete invoice success."""
    patcher, service = setup_service_mock(delete="invoice_abc123")
    try:
        response = client.delete(f"{INVOICES_BASE}/invoice_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "invoice_abc123"
    service.delete.assert_awaited_once_with("invoice_abc123")


def test_append_invoice_timeline_success(client):
    """Test append invoice timeline success."""
    timeline = [
        {
            "id": "evt-2",
            "at": iso_timestamp(),
            "type": "note",
            "note": "Awaiting approval",
        }
    ]
    patcher, service = setup_service_mock(append_timeline=timeline)
    try:
        response = client.post(
            f"{INVOICES_BASE}/invoice_abc123/timeline",
            json={"type": "note", "note": "Awaiting approval"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"][0]["type"] == "note"
    service.append_timeline.assert_awaited_once()
