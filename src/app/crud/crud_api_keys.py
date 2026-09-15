"""Database operations for API keys."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.schemas.common import RecordStatus


class CRUDApiKey:
    """CRUD operations for API keys."""

    async def get_by_hash(self, db: AsyncSession, key_hash: str) -> dict[str, Any] | None:
        """Return an active API key by hash or None if not found."""
        stmt = select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _api_key_to_dict(row) if row else None

    async def get_by_tenant_project(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
    ) -> dict[str, Any] | None:
        """Return an active API key for a tenant/project or None if not found."""
        stmt = select(ApiKey).where(
            ApiKey.tenant_id == tenant_id,
            ApiKey.project_id == project_id,
            ApiKey.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _api_key_to_dict(row) if row else None

    async def get_public_by_tenant_project(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
    ) -> dict[str, Any] | None:
        """Return public API key metadata for a tenant/project or None if not found."""
        stmt = select(ApiKey).where(
            ApiKey.tenant_id == tenant_id,
            ApiKey.project_id == project_id,
            ApiKey.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _public_api_key_dict(row) if row else None

    async def touch_last_used(self, db: AsyncSession, api_key_id: str) -> None:
        """Update the last-used timestamp for an API key."""
        stmt = update(ApiKey).where(ApiKey.id == api_key_id).values(last_used_at=datetime.now(UTC))
        await db.execute(stmt)

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        entity_id: str,
        tenant_id: str,
        project_id: str,
    ) -> bool:
        """Soft-delete an active API key and return whether a row was updated."""
        stmt = (
            update(ApiKey)
            .where(
                ApiKey.id == entity_id,
                ApiKey.tenant_id == tenant_id,
                ApiKey.project_id == project_id,
                ApiKey.record_status == RecordStatus.ACTIVE.value,
            )
            .values(
                record_status=RecordStatus.DELETED.value,
                deleted_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await db.execute(stmt)
        return result.rowcount == 1

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        name: str,
        key_prefix: str,
        key_hash: str,
    ) -> dict[str, Any]:
        """Create a new API key record."""
        row = ApiKey(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _public_api_key_dict(row)

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new API key rows."""
        return f"api_key_{uuid.uuid4().hex[:12]}"


def _api_key_to_dict(row: ApiKey) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "key_prefix": row.key_prefix,
        "key_hash": row.key_hash,
        "last_used_at": row.last_used_at,
    }


def _public_api_key_dict(row: ApiKey) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "key_prefix": row.key_prefix,
        "last_used_at": row.last_used_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_api_keys = CRUDApiKey()
