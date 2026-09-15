"""Database operations for work orders."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.timeline import new_timeline_event
from app.models.work_order import WorkOrder
from app.schemas.common import RecordStatus
from app.schemas.work_orders import WorkOrderState


class CRUDWorkOrder:
    """CRUD operations for work orders."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        state: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List active work orders and return rows with the total count."""
        filters = [
            WorkOrder.tenant_id == tenant_id,
            WorkOrder.project_id == project_id,
            WorkOrder.record_status == RecordStatus.ACTIVE.value,
        ]
        if state:
            filters.append(WorkOrder.state == state)

        count_stmt = select(func.count()).select_from(WorkOrder).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(WorkOrder)
            .where(*filters)
            .order_by(WorkOrder.scheduled_date.asc().nulls_last(), WorkOrder.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_work_order_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active work order by ID or None if not found."""
        stmt = select(WorkOrder).where(
            WorkOrder.id == entity_id,
            WorkOrder.tenant_id == tenant_id,
            WorkOrder.project_id == project_id,
            WorkOrder.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _work_order_to_dict(row) if row else None

    async def get_by_vendor_token_hash(
        self,
        db: AsyncSession,
        token_hash: str,
    ) -> dict[str, Any] | None:
        """Return an active work order by vendor token hash or None if not found."""
        stmt = select(WorkOrder).where(
            WorkOrder.vendor_token_hash == token_hash,
            WorkOrder.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _work_order_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new work order record."""
        row = WorkOrder(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _work_order_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active work order and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(WorkOrder)
            .where(
                WorkOrder.id == entity_id,
                WorkOrder.tenant_id == tenant_id,
                WorkOrder.project_id == project_id,
                WorkOrder.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(WorkOrder)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _work_order_to_dict(row) if row else None

    async def append_timeline(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        event: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        """Append a timeline event to a work order and return the updated timeline or None."""
        record = await self.get_by_id(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            entity_id=entity_id,
        )
        if not record:
            return None

        timeline = list(record.get("timeline") or [])
        timeline.append(new_timeline_event(event))
        updated = await self.update(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            entity_id=entity_id,
            data={"timeline": timeline},
        )
        return list(updated["timeline"]) if updated else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active work order and return whether a row was updated."""
        stmt = (
            update(WorkOrder)
            .where(
                WorkOrder.id == entity_id,
                WorkOrder.tenant_id == tenant_id,
                WorkOrder.project_id == project_id,
                WorkOrder.record_status == RecordStatus.ACTIVE.value,
            )
            .values(
                record_status=RecordStatus.DELETED.value,
                deleted_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await db.execute(stmt)
        return result.rowcount == 1

    async def existing_contract_schedule_dates(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> set[str]:
        """Return scheduled dates already used by contract-sourced work orders."""
        stmt = select(WorkOrder.scheduled_date).where(
            WorkOrder.contract_id == contract_id,
            WorkOrder.source == "contract",
            WorkOrder.state != "terminated",
            WorkOrder.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        return {str(row[0])[:10] for row in result.all() if row[0]}

    async def cancel_contract_work_orders(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
    ) -> int:
        """Terminate upcoming contract-sourced work orders and return the number updated."""
        stmt = (
            update(WorkOrder)
            .where(
                WorkOrder.contract_id == contract_id,
                WorkOrder.source == "contract",
                WorkOrder.state == "upcoming",
                WorkOrder.record_status == RecordStatus.ACTIVE.value,
            )
            .values(state="terminated", updated_at=datetime.now(UTC))
        )
        result = await db.execute(stmt)
        return result.rowcount or 0

    async def cancel_recurring_children(
        self,
        db: AsyncSession,
        *,
        template_id: str,
        note: str,
    ) -> int:
        """Terminate upcoming recurring child work orders and return the number updated."""
        stmt = select(WorkOrder).where(
            WorkOrder.recurring_parent_id == template_id,
            WorkOrder.state == WorkOrderState.UPCOMING.value,
            WorkOrder.started_at.is_(None),
            WorkOrder.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        if not rows:
            return 0

        event = new_timeline_event(
            {
                "type": "status_changed",
                "by": "Scheduler",
                "note": note,
            }
        )
        count = 0
        for row in rows:
            timeline = list(row.timeline or [])
            timeline.append(event)
            update_stmt = (
                update(WorkOrder)
                .where(WorkOrder.id == row.id)
                .values(
                    state=WorkOrderState.TERMINATED.value,
                    timeline=timeline,
                    updated_at=datetime.now(UTC),
                )
            )
            await db.execute(update_stmt)
            count += 1
        return count

    async def list_recurring_templates(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List active recurring work order templates for scheduler processing."""
        filters = [
            WorkOrder.is_recurring.is_(True),
            WorkOrder.state != "terminated",
            WorkOrder.record_status == RecordStatus.ACTIVE.value,
        ]
        if tenant_id:
            filters.append(WorkOrder.tenant_id == tenant_id)
        stmt = select(WorkOrder).where(*filters)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_work_order_to_dict(row) for row in rows]

    async def recurring_child_dates(
        self,
        db: AsyncSession,
        *,
        template_id: str,
    ) -> set[str]:
        """Return scheduled dates already used by recurring child work orders."""
        stmt = select(WorkOrder.scheduled_date).where(
            WorkOrder.recurring_parent_id == template_id,
            WorkOrder.state != "terminated",
            WorkOrder.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        return {str(row[0])[:10] for row in result.all() if row[0]}

    async def update_recurring_next_date(
        self,
        db: AsyncSession,
        *,
        work_order_id: str,
        next_date,
    ) -> None:
        """Update the next recurring generation date for a work order template."""
        stmt = (
            update(WorkOrder)
            .where(WorkOrder.id == work_order_id)
            .values(recurring_next_date=next_date, updated_at=datetime.now(UTC))
        )
        await db.execute(stmt)

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new work order rows."""
        return f"work_order_{uuid.uuid4().hex[:12]}"


def _work_order_to_dict(row: WorkOrder) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "title": row.title,
        "description": row.description,
        "asset_ids": list(row.asset_ids or []),
        "contract_id": row.contract_id,
        "vendor_id": row.vendor_id,
        "form_template_id": row.form_template_id,
        "pre_start_form_template_id": row.pre_start_form_template_id,
        "state": row.state,
        "priority": row.priority,
        "source": row.source,
        "scheduled_date": row.scheduled_date,
        "started_at": row.started_at,
        "completed_at": row.completed_at,
        "assignee": row.assignee,
        "assignee_user_id": row.assignee_user_id,
        "line_items": list(row.line_items or []),
        "form_values": dict(row.form_values or {}),
        "pre_start_form_values": dict(row.pre_start_form_values or {}),
        "estimated_cost": row.estimated_cost,
        "access_notes": row.access_notes,
        "is_recurring": row.is_recurring,
        "recurring_frequency": row.recurring_frequency,
        "recurring_days": list(row.recurring_days or []),
        "recurring_end_date": row.recurring_end_date,
        "recurring_parent_id": row.recurring_parent_id,
        "recurring_next_date": row.recurring_next_date,
        "invoice_ids": list(row.invoice_ids or []),
        "vendor_token_hash": row.vendor_token_hash,
        "timeline": list(row.timeline or []),
        "termination_reason": row.termination_reason,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_work_orders = CRUDWorkOrder()
