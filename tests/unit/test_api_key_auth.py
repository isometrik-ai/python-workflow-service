"""Tests for api key auth."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.header_validators import HeaderApiKeyAuth
from app.schemas.common import ApiKeyScope


@pytest.mark.asyncio
async def test_get_api_key_scope_with_valid_api_key(monkeypatch):
    """Test get api key scope with valid api key."""
    tenant_id = "tenant123"
    project_id = "project123"
    api_key_id = "key-1"
    raw_key = "valid-api-key-value-123456"

    mock_service = MagicMock()
    mock_service.resolve_scope = AsyncMock(
        return_value=ApiKeyScope(
            tenant_id=tenant_id,
            project_id=project_id,
            api_key_id=api_key_id,
            api_key_name="test-key",
        )
    )
    monkeypatch.setattr(
        "app.core.security.api_key_auth.ApiKeyService",
        lambda db: mock_service,
    )

    headers = HeaderApiKeyAuth(
        **{
            "x-api-key": raw_key,
            "x-tenant-id": "",
            "x-project-id": "",
        }
    )
    scope = await get_api_key_scope(headers=headers, db=MagicMock())

    assert scope.tenant_id == tenant_id
    assert scope.project_id == project_id
    assert scope.api_key_id == api_key_id
    mock_service.resolve_scope.assert_awaited_once_with(
        raw_api_key=raw_key,
        tenant_id="",
        project_id="",
    )


@pytest.mark.asyncio
async def test_get_api_key_scope_with_tenant_project_headers(monkeypatch):
    """Test get api key scope with tenant project headers."""
    tenant_id = "tenant123"
    project_id = "project123"
    api_key_id = "key-1"

    mock_service = MagicMock()
    mock_service.resolve_scope = AsyncMock(
        return_value=ApiKeyScope(
            tenant_id=tenant_id,
            project_id=project_id,
            api_key_id=api_key_id,
            api_key_name="scoped-key",
        )
    )
    monkeypatch.setattr(
        "app.core.security.api_key_auth.ApiKeyService",
        lambda db: mock_service,
    )

    headers = HeaderApiKeyAuth(
        **{
            "x-api-key": "",
            "x-tenant-id": tenant_id,
            "x-project-id": project_id,
        }
    )
    scope = await get_api_key_scope(headers=headers, db=MagicMock())

    assert scope.tenant_id == tenant_id
    assert scope.project_id == project_id
    mock_service.resolve_scope.assert_awaited_once_with(
        raw_api_key="",
        tenant_id=tenant_id,
        project_id=project_id,
    )
