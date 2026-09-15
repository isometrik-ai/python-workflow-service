"""Database operations for form templates."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.form_template import FormTemplate
from app.schemas.common import RecordStatus


class CRUDFormTemplate:
    """CRUD operations for form templates."""

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
        """List active form templates and return rows with the total count."""
        filters = [
            FormTemplate.tenant_id == tenant_id,
            FormTemplate.project_id == project_id,
            FormTemplate.record_status == RecordStatus.ACTIVE.value,
        ]
        if search:
            filters.append(FormTemplate.name.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count()).select_from(FormTemplate).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        offset = (page - 1) * page_size
        stmt = (
            select(FormTemplate)
            .where(*filters)
            .order_by(FormTemplate.name)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_form_template_to_dict(row) for row in rows], total

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active form template by ID or None if not found."""
        stmt = select(FormTemplate).where(
            FormTemplate.id == entity_id,
            FormTemplate.tenant_id == tenant_id,
            FormTemplate.project_id == project_id,
            FormTemplate.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _form_template_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        name: str,
        description: str = "",
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new form template record."""
        row = FormTemplate(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            description=description,
            schema=schema or {},
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _form_template_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active form template and return the updated record or None."""
        values = {k: v for k, v in data.items() if v is not None}
        if not values:
            return await self.get_by_id(
                db,
                tenant_id=tenant_id,
                project_id=project_id,
                entity_id=entity_id,
            )
        values["updated_at"] = datetime.now(UTC)
        stmt = (
            update(FormTemplate)
            .where(
                FormTemplate.id == entity_id,
                FormTemplate.tenant_id == tenant_id,
                FormTemplate.project_id == project_id,
                FormTemplate.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(FormTemplate)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _form_template_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active form template and return whether a row was updated."""
        stmt = (
            update(FormTemplate)
            .where(
                FormTemplate.id == entity_id,
                FormTemplate.tenant_id == tenant_id,
                FormTemplate.project_id == project_id,
                FormTemplate.record_status == RecordStatus.ACTIVE.value,
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
        """Generate a primary key for new form template rows."""
        return f"form_template_{uuid.uuid4().hex[:12]}"


def _form_template_to_dict(row: FormTemplate) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "description": row.description,
        "schema": row.schema or {},
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_form_templates = CRUDFormTemplate()
