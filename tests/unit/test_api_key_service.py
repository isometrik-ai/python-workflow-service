"""Tests for api key service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.business.services.api_key_service import ApiKeyService
from app.core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from app.core.utils.api_keys import hash_api_key
from app.schemas.common import ApiKeyScope


@pytest.mark.asyncio
async def test_api_key_service_resolve_scope_with_api_key(monkeypatch):
    """Test api key service resolve scope with api key."""
    tenant_id = "tenant123"
    project_id = "project123"
    api_key_id = "key-1"
    raw_key = "valid-api-key-value-123456"

    mock_crud = MagicMock()
    mock_crud.get_by_hash = AsyncMock(
        return_value={
            "id": api_key_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "name": "test-key",
        }
    )
    mock_crud.touch_last_used = AsyncMock()
    monkeypatch.setattr("app.business.services.api_key_service.crud_api_keys", mock_crud)

    service = ApiKeyService(db=MagicMock())
    scope = await service.resolve_scope(raw_api_key=raw_key)

    assert scope == ApiKeyScope(
        tenant_id=tenant_id,
        project_id=project_id,
        api_key_id=api_key_id,
        api_key_name="test-key",
    )
    mock_crud.get_by_hash.assert_awaited_once_with(service.db, hash_api_key(raw_key))
    mock_crud.touch_last_used.assert_awaited_once_with(service.db, api_key_id)


@pytest.mark.asyncio
async def test_api_key_service_get_project_api_key(monkeypatch):
    """Test api key service get project api key."""
    record = {"id": "key-1", "tenant_id": "tenant123", "project_id": "project123"}
    mock_crud = MagicMock()
    mock_crud.get_public_by_tenant_project = AsyncMock(return_value=record)
    monkeypatch.setattr("app.business.services.api_key_service.crud_api_keys", mock_crud)

    service = ApiKeyService(db=MagicMock(), tenant_id="tenant123", project_id="project123")
    result = await service.get_project_api_key()

    assert result == record
    mock_crud.get_public_by_tenant_project.assert_awaited_once_with(
        service.db,
        tenant_id="tenant123",
        project_id="project123",
    )


@pytest.mark.asyncio
async def test_api_key_service_get_project_api_key_not_found(monkeypatch):
    """Test api key service get project api key not found."""
    mock_crud = MagicMock()
    mock_crud.get_public_by_tenant_project = AsyncMock(return_value=None)
    monkeypatch.setattr("app.business.services.api_key_service.crud_api_keys", mock_crud)

    service = ApiKeyService(db=MagicMock(), tenant_id="tenant123", project_id="project123")

    with pytest.raises(NotFoundException):
        await service.get_project_api_key()


@pytest.mark.asyncio
async def test_api_key_service_create_api_key(monkeypatch):
    """Test api key service create api key."""
    created = {
        "id": "key-1",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "name": "Integration Key",
        "key_prefix": "abc123",
        "last_used_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    mock_crud = MagicMock()
    mock_crud.get_by_tenant_project = AsyncMock(return_value=None)
    mock_crud.create = AsyncMock(return_value=created)
    monkeypatch.setattr("app.business.services.api_key_service.crud_api_keys", mock_crud)
    monkeypatch.setattr(
        "app.business.services.api_key_service.generate_api_key",
        lambda: ("raw-key-value", "hash-value", "raw-key-val"),
    )

    service = ApiKeyService(db=MagicMock())
    result = await service.create_api_key(
        tenant_id="tenant123",
        project_id="project123",
        name="Integration Key",
    )

    assert result["key"] == "raw-key-value"
    mock_crud.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_key_service_create_api_key_duplicate(monkeypatch):
    """Test api key service create api key duplicate."""
    mock_crud = MagicMock()
    mock_crud.get_by_tenant_project = AsyncMock(return_value={"id": "key-1"})
    monkeypatch.setattr("app.business.services.api_key_service.crud_api_keys", mock_crud)

    service = ApiKeyService(db=MagicMock())

    with pytest.raises(DuplicateValueException):
        await service.create_api_key(
            tenant_id="tenant123",
            project_id="project123",
            name="Integration Key",
        )
