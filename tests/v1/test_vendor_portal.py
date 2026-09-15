"""Tests for vendor portal."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.vendor_auth import get_work_order_from_vendor_token

VENDOR_BASE = "/api/v1/vendor"
VENDOR_HEADERS = {"x-vendor-token": "vendor-token-1234567890abcd"}


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def work_order_record(**overrides) -> dict:
    """Build a sample work order record for assertions."""
    payload = {
        "id": "work_order_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "title": "Replace filter",
        "description": "Quarterly filter replacement",
        "asset_ids": ["asset_abc123"],
        "contract_id": "contract_abc123",
        "vendor_id": "vendor_abc123",
        "form_template_id": None,
        "pre_start_form_template_id": None,
        "state": "upcoming",
        "priority": "medium",
        "source": "contract",
        "scheduled_date": date(2026, 4, 15),
        "started_at": None,
        "completed_at": None,
        "assignee": "Alex",
        "assignee_user_id": None,
        "line_items": [],
        "form_values": {},
        "pre_start_form_values": {},
        "estimated_cost": 5000,
        "access_notes": "Roof access required",
        "is_recurring": False,
        "recurring_frequency": None,
        "recurring_days": [],
        "recurring_end_date": None,
        "recurring_parent_id": None,
        "recurring_next_date": None,
        "invoice_ids": [],
        "vendor_token_hash": "abc123hash",
        "timeline": [],
        "termination_reason": None,
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def invoice_record(**overrides) -> dict:
    """Build a sample invoice record for assertions."""
    payload = {
        "id": "invoice_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "work_order_id": "work_order_abc123",
        "vendor_id": "vendor_abc123",
        "invoice_number": "INV-V-001",
        "date": date(2026, 4, 20),
        "line_items": [],
        "subtotal": 50000,
        "tax": 9000,
        "total": 59000,
        "currency": "INR",
        "status": "submitted",
        "document": {},
        "files": [],
        "timeline": [],
        "revisions": [],
        "payment_id": None,
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.vendor_portal.VendorPortalService")
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
def override_vendor_auth(client):
    """Override dependencies for vendor auth during tests."""

    def _work_order_override():
        return work_order_record()

    overrides = client.app.dependency_overrides.copy()
    client.app.dependency_overrides[get_work_order_from_vendor_token] = _work_order_override
    yield
    client.app.dependency_overrides.clear()
    client.app.dependency_overrides.update(overrides)


def test_vendor_get_work_order_success(client):
    """Test vendor get work order success."""
    response = client.get(f"{VENDOR_BASE}/work-order", headers=VENDOR_HEADERS)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "work_order_abc123"


def test_vendor_update_work_order_success(client):
    """Test vendor update work order success."""
    updated = work_order_record(state="in_progress")
    patcher, service = setup_service_mock(update_work_order=updated)
    try:
        response = client.patch(
            f"{VENDOR_BASE}/work-order",
            headers=VENDOR_HEADERS,
            json={"state": "in_progress"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["state"] == "in_progress"
    service.update_work_order.assert_awaited_once()


def test_vendor_submit_invoice_success(client):
    """Test vendor submit invoice success."""
    patcher, service = setup_service_mock(submit_invoice=invoice_record())
    try:
        response = client.post(
            f"{VENDOR_BASE}/invoices",
            headers=VENDOR_HEADERS,
            json={
                "invoice_number": "INV-V-001",
                "subtotal": 50000,
                "tax": 9000,
                "total": 59000,
            },
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["data"]["invoice_number"] == "INV-V-001"
    service.submit_invoice.assert_awaited_once()


def test_vendor_list_invoices_success(client):
    """Test vendor list invoices success."""
    patcher, service = setup_service_mock(list_invoices=([invoice_record()], 1))
    try:
        response = client.get(f"{VENDOR_BASE}/invoices", headers=VENDOR_HEADERS)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["status"] == "submitted"
    service.list_invoices.assert_awaited_once()
