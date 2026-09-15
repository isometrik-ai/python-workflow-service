"""Tests for presigned url."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import ServerErrorException
from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

PRESIGNED_URL_BASE = "/api/v1/upload/presigned-url"


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


def test_get_presigned_url_success(client):
    """Test get presigned url success."""
    patcher = patch("app.api.v1.presigned_url.PresignedUrlService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.generate.return_value = {
        "url": "https://example.r2.cloudflarestorage.com/upload?sig=abc",
        "file_name": "invoice.pdf",
        "bucket": "work-order-media",
    }
    service_cls.return_value = instance
    try:
        response = client.get(
            PRESIGNED_URL_BASE,
            params={
                "file_name": "invoice.pdf",
                "path": "tenant123/project123/invoices",
                "bucket": "work-order-media",
                "content_type": "application/pdf",
            },
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["data"]["file_name"] == "invoice.pdf"
    assert body["data"]["bucket"] == "work-order-media"
    instance.generate.assert_called_once()


def test_get_presigned_url_missing_credentials(client):
    """Test get presigned url missing credentials."""
    patcher = patch("app.api.v1.presigned_url.PresignedUrlService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.generate.side_effect = ServerErrorException(
        message_key="presigned_url.errors.r2_credentials_not_configured"
    )
    service_cls.return_value = instance
    try:
        response = client.get(
            PRESIGNED_URL_BASE,
            params={
                "file_name": "invoice.pdf",
                "path": "tenant123/project123/invoices",
                "bucket": "work-order-media",
                "content_type": "application/pdf",
            },
        )
    finally:
        patcher.stop()

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
