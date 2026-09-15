"""Asset category business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import NotFoundException
from app.crud.crud_asset_categories import crud_asset_categories


class AssetCategoryService:
    """Asset category operations scoped to tenant/project."""

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
        """Return paginated asset categories for the tenant/project."""
        return await crud_asset_categories.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            search=search,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one asset category by ID."""
        record = await crud_asset_categories.get_by_id(
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
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new asset category."""
        if parent_id:
            await self._ensure_exists(parent_id)
        return await crud_asset_categories.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            name=name.strip(),
            description=description,
            parent_id=parent_id,
        )

    async def update(
        self,
        entity_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing asset category."""
        if parent_id is not None and parent_id:
            await self._ensure_exists(parent_id)
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name.strip()
        if description is not None:
            data["description"] = description
        if parent_id is not None:
            data["parent_id"] = parent_id or None
        if not data:
            return await self.get(entity_id)

        record = await crud_asset_categories.update(
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
        """Soft-delete an asset category."""
        deleted = await crud_asset_categories.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        return entity_id

    async def _ensure_exists(self, entity_id: str) -> None:
        record = await crud_asset_categories.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
