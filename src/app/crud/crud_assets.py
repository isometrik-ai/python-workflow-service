"""Database operations for assets."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.schemas.common import RecordStatus


class CRUDAsset:
    """CRUD operations for assets."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        category_id: str | None = None,
        status: str | None = None,
        location_id: str | None = None,
        contract_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List active assets and return rows with the total count."""
        filters = [
            Asset.tenant_id == tenant_id,
            Asset.project_id == project_id,
            Asset.record_status == RecordStatus.ACTIVE.value,
        ]
        if category_id:
            filters.append(Asset.category_id == category_id)
        if status:
            filters.append(Asset.status == status)
        if location_id:
            filters.append(Asset.location_id == location_id)
        if contract_id:
            filters.append(Asset.contract_id == contract_id)
        if search:
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    Asset.name.ilike(term),
                    Asset.code.ilike(term),
                    Asset.serial_number.ilike(term),
                )
            )

        count_stmt = select(func.count()).select_from(Asset).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = select(Asset).where(*filters).order_by(Asset.name).offset(offset).limit(page_size)
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_asset_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active asset by ID or None if not found."""
        stmt = select(Asset).where(
            Asset.id == entity_id,
            Asset.tenant_id == tenant_id,
            Asset.project_id == project_id,
            Asset.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _asset_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new asset record."""
        row = Asset(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _asset_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active asset and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(Asset)
            .where(
                Asset.id == entity_id,
                Asset.tenant_id == tenant_id,
                Asset.project_id == project_id,
                Asset.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(Asset)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _asset_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active asset and return whether a row was updated."""
        stmt = (
            update(Asset)
            .where(
                Asset.id == entity_id,
                Asset.tenant_id == tenant_id,
                Asset.project_id == project_id,
                Asset.record_status == RecordStatus.ACTIVE.value,
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
        """Generate a primary key for new asset rows."""
        return f"asset_{uuid.uuid4().hex[:12]}"


def _asset_to_dict(row: Asset) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "code": row.code,
        "make": row.make,
        "model": row.model,
        "serial_number": row.serial_number,
        "description": row.description,
        "category_id": row.category_id,
        "status": row.status,
        "location_id": row.location_id,
        "location_text": row.location_text,
        "landmark_note": row.landmark_note,
        "photos": row.photos or [],
        "associated_parts": row.associated_parts or [],
        "purchase_date": row.purchase_date,
        "purchase_cost": row.purchase_cost,
        "currency": row.currency,
        "supplier": row.supplier,
        "supplier_vendor_id": row.supplier_vendor_id,
        "purchase_order_number": row.purchase_order_number,
        "invoice_ref": row.invoice_ref,
        "install_date": row.install_date,
        "warranty_start": row.warranty_start,
        "warranty_expiry": row.warranty_expiry,
        "warranty_terms": row.warranty_terms,
        "documents": row.documents or [],
        "custom_field_values": row.custom_field_values or {},
        "contract_id": row.contract_id,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_assets = CRUDAsset()
