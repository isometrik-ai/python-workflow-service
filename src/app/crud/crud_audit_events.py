"""Database operations for audit events."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent


class CRUDAuditEvent:
    """Read operations for audit events."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        entity: str | None = None,
        entity_id: str | None = None,
        source: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List audit events and return rows with the total count."""
        filters = [
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.project_id == project_id,
        ]
        if entity:
            filters.append(AuditEvent.entity == entity)
        if entity_id:
            filters.append(AuditEvent.entity_id == entity_id)
        if source:
            filters.append(AuditEvent.source == source)

        count_stmt = select(func.count()).select_from(AuditEvent).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(AuditEvent)
            .where(*filters)
            .order_by(AuditEvent.at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_audit_event_to_dict(row) for row in rows], total

    async def create(
        self,
        db: AsyncSession,
        *,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new audit event record."""
        row = AuditEvent(id=self.new_id(), **data)
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _audit_event_to_dict(row)

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new audit event rows."""
        return f"audit_{uuid.uuid4().hex[:12]}"


def _audit_event_to_dict(row: AuditEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "entity": row.entity,
        "entity_id": row.entity_id,
        "entity_label": row.entity_label,
        "action": row.action,
        "actor": row.actor,
        "source": row.source,
        "changes": list(row.changes or []),
        "snapshot": dict(row.snapshot or {}),
        "at": row.at,
    }


crud_audit_events = CRUDAuditEvent()
