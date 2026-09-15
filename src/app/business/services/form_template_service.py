"""Form template business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import NotFoundException
from app.crud.crud_form_templates import crud_form_templates


class FormTemplateService:
    """Form template operations scoped to tenant/project."""

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

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated form templates for the tenant/project."""
        return await crud_form_templates.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            search=search,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one form template by ID."""
        record = await crud_form_templates.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(
        self,
        *,
        name: str,
        description: str = "",
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new form template."""
        return await crud_form_templates.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            name=name.strip(),
            description=description,
            schema=schema or {},
        )

    async def update(
        self,
        entity_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update an existing form template."""
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name.strip()
        if description is not None:
            data["description"] = description
        if schema is not None:
            data["schema"] = schema
        if not data:
            return await self.get(entity_id)

        record = await crud_form_templates.update(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            data=data,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete a form template."""
        deleted = await crud_form_templates.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        return entity_id
