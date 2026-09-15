"""Tests for work orders."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

WORK_ORDERS_BASE = "/api/v1/work-orders"


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


def create_work_order_payload(**overrides) -> dict:
    """Build a request payload for create work order."""
    payload = {
        "title": "Replace filter",
        "asset_ids": ["asset_abc123"],
        "contract_id": "contract_abc123",
        "vendor_id": "vendor_abc123",
        "scheduled_date": "2026-04-15",
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.work_orders.WorkOrderService")
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


def test_list_work_orders_success(client):
    """Test list work orders success."""
    patcher, service = setup_service_mock(list=([work_order_record()], 1))
    try:
        response = client.get(WORK_ORDERS_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == 1
    assert body["data"][0]["state"] == "upcoming"
    service.list.assert_awaited_once()


def test_get_work_order_success(client):
    """Test get work order success."""
    patcher, service = setup_service_mock(get=work_order_record())
    try:
        response = client.get(f"{WORK_ORDERS_BASE}/work_order_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["title"] == "Replace filter"
    service.get.assert_awaited_once_with("work_order_abc123")


def test_get_work_order_not_found(client):
    """Test get work order not found."""
    patcher, service = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{WORK_ORDERS_BASE}/missing")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get.assert_awaited_once()


def test_create_work_order_success(client):
    """Test create work order success."""
    patcher, service = setup_service_mock(create=work_order_record())
    try:
        response = client.post(WORK_ORDERS_BASE, json=create_work_order_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["data"]["priority"] == "medium"
    service.create.assert_awaited_once()


def test_update_work_order_success(client):
    """Test update work order success."""
    updated = work_order_record(state="in_progress")
    patcher, service = setup_service_mock(update=updated)
    try:
        response = client.patch(
            f"{WORK_ORDERS_BASE}/work_order_abc123",
            json={"state": "in_progress"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["state"] == "in_progress"
    service.update.assert_awaited_once()


def test_delete_work_order_success(client):
    """Test delete work order success."""
    patcher, service = setup_service_mock(delete="work_order_abc123")
    try:
        response = client.delete(f"{WORK_ORDERS_BASE}/work_order_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "work_order_abc123"
    service.delete.assert_awaited_once_with("work_order_abc123")


def test_append_work_order_timeline_success(client):
    """Test append work order timeline success."""
    timeline = [
        {
            "id": "evt-1",
            "at": iso_timestamp(),
            "type": "note",
            "note": "Vendor en route",
            "by": "Alex",
        }
    ]
    patcher, service = setup_service_mock(append_timeline=timeline)
    try:
        response = client.post(
            f"{WORK_ORDERS_BASE}/work_order_abc123/timeline",
            json={"type": "note", "note": "Vendor en route", "by": "Alex"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"][0]["type"] == "note"
    service.append_timeline.assert_awaited_once()
