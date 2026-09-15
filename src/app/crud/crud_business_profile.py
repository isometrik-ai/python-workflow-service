"""Database operations for business profile singleton."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business_profile import BusinessProfile

DEFAULT_PROFILE_ID = "default"


class CRUDBusinessProfile:
    """CRUD operations for business profile."""

    async def get_or_create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
    ) -> dict[str, Any]:
        """Return the business profile for tenant/project, creating an empty row if missing."""
        stmt = select(BusinessProfile).where(
            BusinessProfile.tenant_id == tenant_id,
            BusinessProfile.project_id == project_id,
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            return _business_profile_to_dict(row)

        row = BusinessProfile(
            id=DEFAULT_PROFILE_ID,
            tenant_id=tenant_id,
            project_id=project_id,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _business_profile_to_dict(row)

    async def upsert(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update business profile fields, creating the row if it does not exist."""
        await self.get_or_create(db, tenant_id=tenant_id, project_id=project_id)
        values = {**data, "updated_at": datetime.now(UTC)}
        stmt = (
            update(BusinessProfile)
            .where(
                BusinessProfile.tenant_id == tenant_id,
                BusinessProfile.project_id == project_id,
            )
            .values(**values)
            .returning(BusinessProfile)
        )
        result = await db.execute(stmt)
        row = result.scalar_one()
        return _business_profile_to_dict(row)


def _business_profile_to_dict(row: BusinessProfile) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "name": row.name,
        "legal_name": row.legal_name,
        "gstin": row.gstin,
        "address_line": row.address_line,
        "city": row.city,
        "state": row.state,
        "pincode": row.pincode,
        "phone": row.phone,
        "email": row.email,
        "website": row.website,
        "logo": row.logo or {},
        "bank_name": row.bank_name,
        "bank_account": row.bank_account,
        "bank_ifsc": row.bank_ifsc,
        "default_wo_notes": row.default_wo_notes,
        "default_wo_terms": row.default_wo_terms,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


crud_business_profile = CRUDBusinessProfile()
