"""Database operations for asset categories."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_category import AssetCategory
from app.schemas.common import RecordStatus


class CRUDAssetCategory:
    """CRUD operations for asset categories."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List active asset categories and return rows with the total count."""
        filters = [
            AssetCategory.tenant_id == tenant_id,
            AssetCategory.project_id == project_id,
            AssetCategory.record_status == RecordStatus.ACTIVE.value,
        ]
        if search:
            filters.append(AssetCategory.name.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count()).select_from(AssetCategory).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(AssetCategory)
            .where(*filters)
            .order_by(AssetCategory.name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_asset_category_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active asset category by ID or None if not found."""
        stmt = select(AssetCategory).where(
            AssetCategory.id == entity_id,
            AssetCategory.tenant_id == tenant_id,
            AssetCategory.project_id == project_id,
            AssetCategory.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _asset_category_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        name: str,
        description: str = "",
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new asset category record."""
        row = AssetCategory(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            description=description,
            parent_id=parent_id,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _asset_category_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active asset category and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(AssetCategory)
            .where(
                AssetCategory.id == entity_id,
                AssetCategory.tenant_id == tenant_id,
                AssetCategory.project_id == project_id,
                AssetCategory.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(AssetCategory)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _asset_category_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active asset category and return whether a row was updated."""
        stmt = (
            update(AssetCategory)
            .where(
                AssetCategory.id == entity_id,
                AssetCategory.tenant_id == tenant_id,
                AssetCategory.project_id == project_id,
                AssetCategory.record_status == RecordStatus.ACTIVE.value,
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
        """Generate a primary key for new asset category rows."""
        return f"asset_category_{uuid.uuid4().hex[:12]}"


def _asset_category_to_dict(row: AssetCategory) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "description": row.description,
        "parent_id": row.parent_id,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_asset_categories = CRUDAssetCategory()
