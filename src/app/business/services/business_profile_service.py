"""Business profile business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_business_profile import crud_business_profile


class BusinessProfileService:
    """Business profile singleton operations scoped to tenant/project."""

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

    async def get(self) -> dict[str, Any]:
        """Return the business profile, auto-creating an empty row if missing."""
        return await crud_business_profile.get_or_create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )

    async def upsert(self, data: dict[str, Any]) -> dict[str, Any]:
        """Upsert business profile fields."""
        payload = {key: value for key, value in data.items() if value is not None}
        return await crud_business_profile.upsert(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            data=payload,
        )
