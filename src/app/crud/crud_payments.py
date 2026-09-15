"""Database operations for payments."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.schemas.common import RecordStatus


class CRUDPayment:
    """CRUD operations for payments."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        invoice_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List active payments and return rows with the total count."""
        filters = [
            Payment.tenant_id == tenant_id,
            Payment.project_id == project_id,
            Payment.record_status == RecordStatus.ACTIVE.value,
        ]
        if invoice_id:
            filters.append(Payment.invoice_id == invoice_id)

        count_stmt = select(func.count()).select_from(Payment).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(Payment)
            .where(*filters)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_payment_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active payment by ID or None if not found."""
        stmt = select(Payment).where(
            Payment.id == entity_id,
            Payment.tenant_id == tenant_id,
            Payment.project_id == project_id,
            Payment.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _payment_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new payment record."""
        row = Payment(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _payment_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active payment and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(Payment)
            .where(
                Payment.id == entity_id,
                Payment.tenant_id == tenant_id,
                Payment.project_id == project_id,
                Payment.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(Payment)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _payment_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active payment and return whether a row was updated."""
        stmt = (
            update(Payment)
            .where(
                Payment.id == entity_id,
                Payment.tenant_id == tenant_id,
                Payment.project_id == project_id,
                Payment.record_status == RecordStatus.ACTIVE.value,
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
        """Generate a primary key for new payment rows."""
        return f"payment_{uuid.uuid4().hex[:12]}"


def _payment_to_dict(row: Payment) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "invoice_id": row.invoice_id,
        "work_order_id": row.work_order_id,
        "amount": row.amount,
        "currency": row.currency,
        "method": row.method,
        "reference": row.reference,
        "date": row.date,
        "status": row.status,
        "receipt": dict(row.receipt or {}),
        "notes": row.notes,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_payments = CRUDPayment()
