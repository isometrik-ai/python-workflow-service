"""Database operations for webhook trigger configurations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger_config import TriggerConfig
from app.schemas.common import RecordStatus


class CRUDTrigger:
    """CRUD operations for webhook trigger configurations."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
    ) -> list[dict[str, Any]]:
        """List active webhook trigger configurations for a tenant/project."""
        stmt = (
            select(TriggerConfig)
            .where(
                TriggerConfig.tenant_id == tenant_id,
                TriggerConfig.project_id == project_id,
                TriggerConfig.record_status == RecordStatus.ACTIVE.value,
            )
            .order_by(TriggerConfig.name)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_trigger_to_dict(row) for row in rows]

    async def list_matching_triggers(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity: str,
        event: str,
    ) -> list[dict[str, Any]]:
        """List active triggers matching an entity and event."""
        stmt = select(TriggerConfig).where(
            TriggerConfig.tenant_id == tenant_id,
            TriggerConfig.project_id == project_id,
            TriggerConfig.entity == entity,
            TriggerConfig.event == event,
            TriggerConfig.is_active.is_(True),
            TriggerConfig.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_trigger_to_dict(row) for row in rows]

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active trigger configuration by ID or None if not found."""
        stmt = select(TriggerConfig).where(
            TriggerConfig.id == entity_id,
            TriggerConfig.tenant_id == tenant_id,
            TriggerConfig.project_id == project_id,
            TriggerConfig.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _trigger_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new trigger configuration record."""
        row = TriggerConfig(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _trigger_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active trigger configuration and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(TriggerConfig)
            .where(
                TriggerConfig.id == entity_id,
                TriggerConfig.tenant_id == tenant_id,
                TriggerConfig.project_id == project_id,
                TriggerConfig.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(TriggerConfig)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _trigger_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active trigger configuration and return whether a row was updated."""
        stmt = (
            update(TriggerConfig)
            .where(
                TriggerConfig.id == entity_id,
                TriggerConfig.tenant_id == tenant_id,
                TriggerConfig.project_id == project_id,
                TriggerConfig.record_status == RecordStatus.ACTIVE.value,
            )
            .values(
                record_status=RecordStatus.DELETED.value,
                deleted_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await db.execute(stmt)
        return result.rowcount == 1

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new trigger configuration rows."""
        return f"trigger_{uuid.uuid4().hex[:12]}"


def _trigger_to_dict(row: TriggerConfig) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "entity": row.entity,
        "event": row.event,
        "is_active": row.is_active,
        "webhook_url": row.webhook_url,
        "secret": row.secret,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_triggers = CRUDTrigger()
