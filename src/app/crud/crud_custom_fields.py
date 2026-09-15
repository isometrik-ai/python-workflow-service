"""Database operations for custom field definitions."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_field import CustomField
from app.schemas.common import RecordStatus


class CRUDCustomField:
    """CRUD operations for custom fields."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        scope: str | None = None,
        category_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List active custom fields and return rows with the total count."""
        filters = [
            CustomField.tenant_id == tenant_id,
            CustomField.project_id == project_id,
            CustomField.record_status == RecordStatus.ACTIVE.value,
        ]
        if scope:
            filters.append(CustomField.scope == scope)
        if category_id:
            filters.append(CustomField.category_id == category_id)
        if search:
            term = f"%{search.strip()}%"
            filters.append(
                or_(
                    CustomField.field_name.ilike(term),
                    CustomField.field_key.ilike(term),
                )
            )

        count_stmt = select(func.count()).select_from(CustomField).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(CustomField)
            .where(*filters)
            .order_by(CustomField.sort_order, CustomField.field_name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_custom_field_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active custom field by ID or None if not found."""
        stmt = select(CustomField).where(
            CustomField.id == entity_id,
            CustomField.tenant_id == tenant_id,
            CustomField.project_id == project_id,
            CustomField.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _custom_field_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new custom field record."""
        row = CustomField(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _custom_field_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active custom field and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(CustomField)
            .where(
                CustomField.id == entity_id,
                CustomField.tenant_id == tenant_id,
                CustomField.project_id == project_id,
                CustomField.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(CustomField)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _custom_field_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active custom field and return whether a row was updated."""
        stmt = (
            update(CustomField)
            .where(
                CustomField.id == entity_id,
                CustomField.tenant_id == tenant_id,
                CustomField.project_id == project_id,
                CustomField.record_status == RecordStatus.ACTIVE.value,
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
        """Generate a primary key for new custom field rows."""
        return f"custom_field_{uuid.uuid4().hex[:12]}"


def _custom_field_to_dict(row: CustomField) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "field_name": row.field_name,
        "field_key": row.field_key,
        "field_type": row.field_type,
        "type_config": row.type_config or {},
        "is_required": row.is_required,
        "is_active": row.is_active,
        "sort_order": row.sort_order,
        "show_on_create": row.show_on_create,
        "show_on_detail": row.show_on_detail,
        "scope": row.scope,
        "category_id": row.category_id,
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_custom_fields = CRUDCustomField()
