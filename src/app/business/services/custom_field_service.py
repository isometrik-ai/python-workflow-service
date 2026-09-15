"""Custom field business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import NotFoundException, ValidationException
from app.crud.crud_asset_categories import crud_asset_categories
from app.crud.crud_custom_fields import crud_custom_fields


class CustomFieldService:
    """Custom field operations scoped to tenant/project."""

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
        scope: str | None = None,
        category_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated custom fields for the tenant/project."""
        return await crud_custom_fields.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            search=search,
            scope=scope,
            category_id=category_id,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one custom field by ID."""
        record = await crud_custom_fields.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new custom field definition."""
        payload = self._prepare_payload(data)
        await self._validate_scope(payload)
        return await crud_custom_fields.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            data=payload,
        )

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing custom field definition."""
        payload = self._prepare_payload(data, partial=True)
        if payload:
            await self._validate_scope(payload)
        if not payload:
            return await self.get(entity_id)
        record = await crud_custom_fields.update(
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
        """Soft-delete a custom field definition."""
        deleted = await crud_custom_fields.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        return entity_id

    async def _validate_scope(self, payload: dict[str, Any]) -> None:
        scope = payload.get("scope")
        category_id = payload.get("category_id")
        if scope == "category" and not category_id:
            raise ValidationException(message_key="errors.validation_failed")
        if category_id:
            record = await crud_asset_categories.get_by_id(
                self.db,
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                entity_id=category_id,
            )
            if not record:
                raise NotFoundException(message_key="errors.not_found")

    @staticmethod
    def _prepare_payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if value is None and partial:
                continue
            if key in ("field_name", "field_key") and isinstance(value, str):
                payload[key] = value.strip()
            else:
                payload[key] = value
        if not partial:
            payload.setdefault("type_config", {})
        return payload
