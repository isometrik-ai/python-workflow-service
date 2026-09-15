"""PDF template business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import NotFoundException
from app.crud.crud_pdf_templates import crud_pdf_templates


class PdfTemplateService:
    """PDF template operations scoped to tenant/project."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
    ) -> None:
        """Initialize the service with database session and tenant scope."""
        self.db = db
        self.tenant_id = tenant_id
        self.project_id = project_id

    async def list(self) -> list[dict[str, Any]]:
        """Return all active PDF templates for the tenant/project."""
        return await crud_pdf_templates.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one PDF template by ID."""
        record = await crud_pdf_templates.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new PDF template."""
        payload = dict(data)
        payload.setdefault("schemas", [])
        return await crud_pdf_templates.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            data=payload,
        )

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing PDF template."""
        payload = {key: value for key, value in data.items() if value is not None}
        if not payload:
            return await self.get(entity_id)
        record = await crud_pdf_templates.update(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            data=payload,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete a PDF template."""
        deleted = await crud_pdf_templates.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        return entity_id
