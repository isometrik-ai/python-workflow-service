"""Database operations for PDF templates."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pdf_template import PdfTemplate
from app.schemas.common import RecordStatus


class CRUDPdfTemplate:
    """CRUD operations for PDF templates."""

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
    ) -> list[dict[str, Any]]:
        """List active PDF templates ordered by creation time."""
        stmt = (
            select(PdfTemplate)
            .where(
                PdfTemplate.tenant_id == tenant_id,
                PdfTemplate.project_id == project_id,
                PdfTemplate.record_status == RecordStatus.ACTIVE.value,
            )
            .order_by(PdfTemplate.created_at.asc())
        )
        result = await db.execute(stmt)
        return [_pdf_template_to_dict(row) for row in result.scalars().all()]

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> dict[str, Any] | None:
        """Return an active PDF template by ID or None if not found."""
        stmt = select(PdfTemplate).where(
            PdfTemplate.id == entity_id,
            PdfTemplate.tenant_id == tenant_id,
            PdfTemplate.project_id == project_id,
            PdfTemplate.record_status == RecordStatus.ACTIVE.value,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        return _pdf_template_to_dict(row) if row else None

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new PDF template record."""
        row = PdfTemplate(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            **data,
        )
        db.add(row)
        await db.flush()
        if row.is_default:
            await self._clear_other_defaults(
                db,
                tenant_id=tenant_id,
                project_id=project_id,
                doc_type=row.doc_type,
                keep_id=row.id,
            )
        await db.refresh(row)
        return _pdf_template_to_dict(row)

    async def update(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an active PDF template and return the updated record or None."""
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(PdfTemplate)
            .where(
                PdfTemplate.id == entity_id,
                PdfTemplate.tenant_id == tenant_id,
                PdfTemplate.project_id == project_id,
                PdfTemplate.record_status == RecordStatus.ACTIVE.value,
            )
            .values(**values)
            .returning(PdfTemplate)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row.is_default:
            await self._clear_other_defaults(
                db,
                tenant_id=tenant_id,
                project_id=project_id,
                doc_type=row.doc_type,
                keep_id=row.id,
            )
        return _pdf_template_to_dict(row) if row else None

    async def soft_delete(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        entity_id: str,
    ) -> bool:
        """Soft-delete an active PDF template and return whether a row was updated."""
        stmt = (
            update(PdfTemplate)
            .where(
                PdfTemplate.id == entity_id,
                PdfTemplate.tenant_id == tenant_id,
                PdfTemplate.project_id == project_id,
                PdfTemplate.record_status == RecordStatus.ACTIVE.value,
            )
            .values(
                record_status=RecordStatus.DELETED.value,
                deleted_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                is_default=False,
            )
        )
        result = await db.execute(stmt)
        return result.rowcount == 1

    async def _clear_other_defaults(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        doc_type: str,
        keep_id: str,
    ) -> None:
        """Unset is_default on other templates of the same doc_type."""
        stmt = (
            update(PdfTemplate)
            .where(
                PdfTemplate.tenant_id == tenant_id,
                PdfTemplate.project_id == project_id,
                PdfTemplate.doc_type == doc_type,
                PdfTemplate.record_status == RecordStatus.ACTIVE.value,
                PdfTemplate.is_default.is_(True),
                PdfTemplate.id != keep_id,
            )
            .values(is_default=False, updated_at=datetime.now(UTC))
        )
        await db.execute(stmt)

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new PDF template rows."""
        return f"pdf_template_{uuid.uuid4().hex[:12]}"


def _pdf_template_to_dict(row: PdfTemplate) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "doc_type": row.doc_type,
        "is_default": row.is_default,
        "base_pdf": row.base_pdf,
        "schemas": row.schemas or [],
        "record_status": row.record_status,
        "deleted_at": row.deleted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_pdf_templates = CRUDPdfTemplate()
