"""Database operations for vendor invoices."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils.timeline import new_timeline_event
from app.models.vendor_invoice import VendorInvoice
from app.schemas.common import RecordStatus


class CRUDInvoice:
    """CRUD operations for vendor invoices."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        work_order_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List active vendor invoices and return rows with the total count."""
        filters = [
            VendorInvoice.tenant_id == tenant_id,
            VendorInvoice.project_id == project_id,
            VendorInvoice.record_status == RecordStatus.ACTIVE.value,
        ]
        if work_order_id:
            filters.append(VendorInvoice.work_order_id == work_order_id)
        if status:
            filters.append(VendorInvoice.status == status)

        count_stmt = select(func.count()).select_from(VendorInvoice).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(VendorInvoice)
            .where(*filters)
            .order_by(VendorInvoice.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_invoice_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active vendor invoice by ID or None if not found."""
        stmt = select(VendorInvoice).where(
            VendorInvoice.id == entity_id,
            VendorInvoice.tenant_id == tenant_id,
            VendorInvoice.project_id == project_id,
            VendorInvoice.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _invoice_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new vendor invoice record."""
        row = VendorInvoice(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _invoice_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active vendor invoice and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(VendorInvoice)
            .where(
                VendorInvoice.id == entity_id,
                VendorInvoice.tenant_id == tenant_id,
                VendorInvoice.project_id == project_id,
                VendorInvoice.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(VendorInvoice)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _invoice_to_dict(row) if row else None

    async def append_timeline(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        event: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        """Append a timeline event to a vendor invoice and return the updated timeline or None."""
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
        """Soft-delete an active vendor invoice and return whether a row was updated."""
        stmt = (
            update(VendorInvoice)
            .where(
                VendorInvoice.id == entity_id,
                VendorInvoice.tenant_id == tenant_id,
                VendorInvoice.project_id == project_id,
                VendorInvoice.record_status == RecordStatus.ACTIVE.value,
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
        """Generate a primary key for new vendor invoice rows."""
        return f"invoice_{uuid.uuid4().hex[:12]}"


def _invoice_to_dict(row: VendorInvoice) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "work_order_id": row.work_order_id,
        "vendor_id": row.vendor_id,
        "invoice_number": row.invoice_number,
        "date": row.date,
        "line_items": list(row.line_items or []),
        "subtotal": row.subtotal,
        "tax": row.tax,
        "total": row.total,
        "currency": row.currency,
        "status": row.status,
        "document": dict(row.document or {}),
        "files": list(row.files or []),
        "timeline": list(row.timeline or []),
        "revisions": list(row.revisions or []),
        "payment_id": row.payment_id,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_invoices = CRUDInvoice()
