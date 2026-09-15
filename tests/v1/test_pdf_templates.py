"""Tests for PDF templates."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

PDF_TEMPLATES_BASE = "/api/v1/pdf-templates"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pdf_template_record(**overrides) -> dict:
    """Build a sample PDF template record."""
    payload = {
        "id": "pdf_template_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Default WO",
        "doc_type": "work_order",
        "is_default": True,
        "base_pdf": None,
        "schemas": [],
        "record_status": "active",
        "deleted_at": None,
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


def test_list_pdf_templates_success(client):
    """List PDF templates returns envelope."""
    patcher = patch("app.api.v1.pdf_templates.PdfTemplateService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.list = AsyncMock(return_value=[pdf_template_record()])
    service_cls.return_value = instance
    try:
        response = client.get(PDF_TEMPLATES_BASE)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"][0]["doc_type"] == "work_order"
    finally:
        patcher.stop()


def test_create_pdf_template_success(client):
    """Create PDF template returns 201."""
    patcher = patch("app.api.v1.pdf_templates.PdfTemplateService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.create = AsyncMock(return_value=pdf_template_record())
    service_cls.return_value = instance
    try:
        response = client.post(PDF_TEMPLATES_BASE, json={"name": "Default WO"})
        assert response.status_code == status.HTTP_201_CREATED
    finally:
        patcher.stop()
