"""Tests for form templates."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import NotFoundException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

FORM_TEMPLATES_BASE = "/api/v1/form-templates"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def form_template_record(**overrides) -> dict:
    """Build a sample form template record for assertions."""
    payload = {
        "id": "form_template_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Work Order Form",
        "description": "Default work order intake",
        "schema": {"type": "object", "properties": {"title": {"type": "string"}}},
        "record_status": "active",
        "deleted_at": None,
        "created_at": iso_timestamp(),
        "updated_at": iso_timestamp(),
    }
    payload.update(overrides)
    return payload


def create_form_template_payload(**overrides) -> dict:
    """Build a request payload for create form template."""
    payload = {
        "name": "Work Order Form",
        "description": "Default work order intake",
        "schema": {"type": "object", "properties": {"title": {"type": "string"}}},
    }
    payload.update(overrides)
    return payload


def setup_service_mock(**async_methods):
    """Configure mocks for service mock."""
    patcher = patch("app.api.v1.form_templates.FormTemplateService")
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


def test_list_form_templates_success(client):
    """Test list form templates success."""
    patcher, service = setup_service_mock(list=([form_template_record()], 1))
    try:
        response = client.get(FORM_TEMPLATES_BASE)
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "success"
    assert body["total"] == 1
    assert body["data"][0]["schema"]["type"] == "object"
    service.list.assert_awaited_once()


def test_get_form_template_success(client):
    """Test get form template success."""
    patcher, service = setup_service_mock(get=form_template_record())
    try:
        response = client.get(f"{FORM_TEMPLATES_BASE}/form_template_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["name"] == "Work Order Form"
    assert body["data"]["schema"]["type"] == "object"
    service.get.assert_awaited_once_with("form_template_abc123")


def test_get_form_template_not_found(client):
    """Test get form template not found."""
    patcher, service = setup_service_mock(get=NotFoundException(message_key="errors.not_found"))
    try:
        response = client.get(f"{FORM_TEMPLATES_BASE}/missing")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_404_NOT_FOUND
    service.get.assert_awaited_once()


def test_create_form_template_success(client):
    """Test create form template success."""
    patcher, service = setup_service_mock(create=form_template_record())
    try:
        response = client.post(FORM_TEMPLATES_BASE, json=create_form_template_payload())
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["data"]["schema"]["type"] == "object"
    service.create.assert_awaited_once_with(
        name="Work Order Form",
        description="Default work order intake",
        schema={"type": "object", "properties": {"title": {"type": "string"}}},
    )


def test_update_form_template_success(client):
    """Test update form template success."""
    updated = form_template_record(name="Updated Form")
    patcher, service = setup_service_mock(update=updated)
    try:
        response = client.patch(
            f"{FORM_TEMPLATES_BASE}/form_template_abc123",
            json={"name": "Updated Form"},
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["name"] == "Updated Form"
    service.update.assert_awaited_once()


def test_delete_form_template_success(client):
    """Test delete form template success."""
    patcher, service = setup_service_mock(delete="form_template_abc123")
    try:
        response = client.delete(f"{FORM_TEMPLATES_BASE}/form_template_abc123")
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["id"] == "form_template_abc123"
    service.delete.assert_awaited_once_with("form_template_abc123")
