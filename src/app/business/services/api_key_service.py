"""API key business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants.status_codes import CustomStatusCode
from app.core.exceptions.http_exceptions import (
    DuplicateValueException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.utils.api_keys import MIN_API_KEY_LENGTH, generate_api_key, hash_api_key
from app.crud.crud_api_keys import crud_api_keys
from app.schemas.common import ApiKeyScope


class ApiKeyService:
    """Resolve tenant/project scope and manage API keys."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        """Initialize the service with database session and optional scope."""
        self.db = db
        self.tenant_id = tenant_id
        self.project_id = project_id

    async def resolve_scope(
        self,
        *,
        raw_api_key: str,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> ApiKeyScope:
        """Resolve tenant/project scope from an API key or scope headers."""
        key = (raw_api_key or "").strip()
        if len(key) >= MIN_API_KEY_LENGTH:
            record = await crud_api_keys.get_by_hash(self.db, hash_api_key(key))
            if not record:
                raise UnauthorizedException(
                    message_key="api_keys.errors.invalid",
                    custom_code=CustomStatusCode.UNAUTHORIZED,
                )
            resolved_tenant = record.get("tenant_id")
            resolved_project = record.get("project_id")
            if not resolved_tenant or not resolved_project:
                raise UnauthorizedException(
                    message_key="api_keys.errors.project_required",
                    custom_code=CustomStatusCode.UNAUTHORIZED,
                )
            await crud_api_keys.touch_last_used(self.db, record["id"])
            return ApiKeyScope(
                tenant_id=resolved_tenant,
                project_id=resolved_project,
                api_key_id=record["id"],
                api_key_name=record.get("name"),
            )

        resolved_tenant = (tenant_id or self.tenant_id or "").strip()
        resolved_project = (project_id or self.project_id or "").strip()
        if not resolved_tenant or not resolved_project:
            raise UnauthorizedException(
                message_key="api_keys.errors.missing_or_invalid",
                custom_code=CustomStatusCode.UNAUTHORIZED,
            )

        record = await crud_api_keys.get_by_tenant_project(
            self.db,
            tenant_id=resolved_tenant,
            project_id=resolved_project,
        )
        if not record:
            raise UnauthorizedException(
                message_key="api_keys.errors.invalid_scope",
                custom_code=CustomStatusCode.UNAUTHORIZED,
            )

        return ApiKeyScope(
            tenant_id=record["tenant_id"],
            project_id=record["project_id"],
            api_key_id=record["id"],
            api_key_name=record.get("name"),
        )

    async def get_project_api_key(self) -> dict[str, Any]:
        """Return the single active API key for the authenticated tenant/project."""
        if not self.tenant_id or not self.project_id:
            raise UnauthorizedException(
                message_key="api_keys.errors.missing_or_invalid",
                custom_code=CustomStatusCode.UNAUTHORIZED,
            )
        record = await crud_api_keys.get_public_by_tenant_project(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create_api_key(
        self,
        *,
        tenant_id: str,
        project_id: str,
        name: str,
    ) -> dict[str, Any]:
        """Create the single active API key for a tenant/project."""
        tenant_id = tenant_id.strip()
        project_id = project_id.strip()
        if not tenant_id or not project_id:
            raise UnauthorizedException(
                message_key="api_keys.errors.missing_or_invalid",
                custom_code=CustomStatusCode.UNAUTHORIZED,
            )

        existing = await crud_api_keys.get_by_tenant_project(
            self.db,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        if existing:
            raise DuplicateValueException(message_key="api_keys.errors.already_exists")

        raw_key, key_hash, key_prefix = generate_api_key()
        record = await crud_api_keys.create(
            self.db,
            tenant_id=tenant_id,
            project_id=project_id,
            name=name.strip() or "API Key",
            key_prefix=key_prefix,
            key_hash=key_hash,
        )
        record["key"] = raw_key
        return record

    async def revoke_api_key(self, key_id: str) -> str:
        """Soft-delete the API key for the authenticated tenant/project."""
        if not self.tenant_id or not self.project_id:
            raise UnauthorizedException(
                message_key="api_keys.errors.missing_or_invalid",
                custom_code=CustomStatusCode.UNAUTHORIZED,
            )
        deleted = await crud_api_keys.soft_delete(
            self.db,
            entity_id=key_id,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        return key_id
