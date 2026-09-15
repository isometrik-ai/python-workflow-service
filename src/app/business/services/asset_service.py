"""Asset business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from app.crud.crud_asset_categories import crud_asset_categories
from app.crud.crud_assets import crud_assets
from app.schemas.assets import AssetStatus


class AssetService:
    """Asset operations scoped to tenant/project."""

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
        category_id: str | None = None,
        status: str | None = None,
        location_id: str | None = None,
        contract_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated assets for the tenant/project."""
        return await crud_assets.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            search=search,
            category_id=category_id,
            status=status,
            location_id=location_id,
            contract_id=contract_id,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one asset by ID."""
        record = await crud_assets.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new asset."""
        await self._ensure_category_exists(data["category_id"])
        payload = self._prepare_create_payload(data)
        try:
            return await crud_assets.create(
                self.db,
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                data=payload,
            )
        except IntegrityError as exc:
            raise DuplicateValueException(message_key="assets.errors.duplicate_code") from exc

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing asset."""
        if "category_id" in data and data["category_id"]:
            await self._ensure_category_exists(data["category_id"])
        payload = self._prepare_update_payload(data)
        if not payload:
            return await self.get(entity_id)
        try:
            record = await crud_assets.update(
                self.db,
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                entity_id=entity_id,
                data=payload,
            )
        except IntegrityError as exc:
            raise DuplicateValueException(message_key="assets.errors.duplicate_code") from exc
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete an asset."""
        deleted = await crud_assets.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        return entity_id

    async def _ensure_category_exists(self, category_id: str) -> None:
        record = await crud_asset_categories.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=category_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")

    @staticmethod
    def _prepare_create_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload["name"] = payload["name"].strip()
        payload["code"] = payload["code"].strip()
        if payload.get("status") is None:
            payload["status"] = AssetStatus.OPERATIONAL.value
        elif isinstance(payload["status"], AssetStatus):
            payload["status"] = payload["status"].value
        if payload.get("currency") is None:
            payload["currency"] = "INR"
        return payload

    @staticmethod
    def _prepare_update_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if value is None:
                continue
            if key in ("name", "code") and isinstance(value, str):
                payload[key] = value.strip()
            elif key == "status" and isinstance(value, AssetStatus):
                payload[key] = value.value
            else:
                payload[key] = value
        return payload
