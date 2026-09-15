"""Database operations for maintenance contracts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.maintenance_contract import MaintenanceContract
from app.schemas.common import RecordStatus


class CRUDContract:
    """CRUD operations for maintenance contracts."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List active maintenance contracts and return rows with the total count."""
        filters = [
            MaintenanceContract.tenant_id == tenant_id,
            MaintenanceContract.project_id == project_id,
            MaintenanceContract.record_status == RecordStatus.ACTIVE.value,
        ]
        if status:
            filters.append(MaintenanceContract.status == status)

        count_stmt = select(func.count()).select_from(MaintenanceContract).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(MaintenanceContract)
            .where(*filters)
            .order_by(MaintenanceContract.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_contract_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active maintenance contract by ID or None if not found."""
        stmt = select(MaintenanceContract).where(
            MaintenanceContract.id == entity_id,
            MaintenanceContract.tenant_id == tenant_id,
            MaintenanceContract.project_id == project_id,
            MaintenanceContract.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _contract_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new maintenance contract record."""
        row = MaintenanceContract(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _contract_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active maintenance contract and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(MaintenanceContract)
            .where(
                MaintenanceContract.id == entity_id,
                MaintenanceContract.tenant_id == tenant_id,
                MaintenanceContract.project_id == project_id,
                MaintenanceContract.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(MaintenanceContract)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _contract_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active maintenance contract and return whether a row was updated."""
        stmt = (
            update(MaintenanceContract)
            .where(
                MaintenanceContract.id == entity_id,
                MaintenanceContract.tenant_id == tenant_id,
                MaintenanceContract.project_id == project_id,
                MaintenanceContract.record_status == RecordStatus.ACTIVE.value,
            )
            .values(
                record_status=RecordStatus.DELETED.value,
                deleted_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        result = await db.execute(stmt)
        return result.rowcount == 1

    async def list_active_for_scheduler(
        self,
        db: AsyncSession,
        *,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List active maintenance contracts for scheduler processing."""
        filters = [MaintenanceContract.record_status == RecordStatus.ACTIVE.value]
        if tenant_id:
            filters.append(MaintenanceContract.tenant_id == tenant_id)
        stmt = select(MaintenanceContract).where(*filters)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_contract_to_dict(row) for row in rows]

    async def update_next_visit_date(
        self,
        db: AsyncSession,
        *,
        contract_id: str,
        next_visit_date,
    ) -> None:
        """Update the next visit date for a maintenance contract."""
        stmt = (
            update(MaintenanceContract)
            .where(MaintenanceContract.id == contract_id)
            .values(next_visit_date=next_visit_date, updated_at=datetime.now(UTC))
        )
        await db.execute(stmt)

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new maintenance contract rows."""
        return f"contract_{uuid.uuid4().hex[:12]}"


def _contract_to_dict(row: MaintenanceContract) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "title": row.title,
        "vendor_id": row.vendor_id,
        "asset_ids": list(row.asset_ids or []),
        "start_date": row.start_date,
        "end_date": row.end_date,
        "visit_frequency": row.visit_frequency,
        "payment_frequency": row.payment_frequency,
        "value": row.value,
        "currency": row.currency,
        "status": row.status,
        "next_visit_date": row.next_visit_date,
        "last_serviced_date": row.last_serviced_date,
        "auto_generate_lead_days": row.auto_generate_lead_days,
        "scope_included": row.scope_included,
        "scope_excluded": row.scope_excluded,
        "form_template_id": row.form_template_id,
        "pre_start_form_template_id": row.pre_start_form_template_id,
        "documents": list(row.documents or []),
        "termination_reason": row.termination_reason,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_contracts = CRUDContract()
