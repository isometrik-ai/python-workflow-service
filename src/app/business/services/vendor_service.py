"""Vendor list/search/create backed by HoA CRM with local asset fallback."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services import hoa_service
from app.models.asset import Asset
from app.schemas.common import RecordStatus

_SEEDED_VENDORS = (
    {"id": "ven-1", "name": "Blue Star HVAC Services"},
    {"id": "ven-2", "name": "PowerGen Electric"},
    {"id": "ven-3", "name": "AquaCare Plumbing"},
)


class VendorService:
    """Vendor operations using HoA with tenant/project-scoped local fallback."""

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

    async def list_local_vendors(self) -> list[dict[str, Any]]:
        """Build a deduplicated vendor list from assets and seeded defaults."""
        stmt = (
            select(Asset.supplier_vendor_id, Asset.supplier)
            .where(
                Asset.tenant_id == self.tenant_id,
                Asset.project_id == self.project_id,
                Asset.record_status == RecordStatus.ACTIVE.value,
                Asset.supplier_vendor_id.is_not(None),
                Asset.supplier.is_not(None),
            )
            .distinct()
        )
        result = await self.db.execute(stmt)
        local = [
            {"id": row.supplier_vendor_id, "name": row.supplier, "source": "local"}
            for row in result
            if row.supplier_vendor_id and row.supplier
        ]
        seen_ids = {vendor["id"] for vendor in local}
        for seeded in _SEEDED_VENDORS:
            if seeded["id"] not in seen_ids:
                local.append({**seeded, "source": "local"})
        return local

    async def list(self, *, query: str | None = None) -> dict[str, Any]:
        """List vendors merged from HoA and local fallback."""
        local = await self.list_local_vendors()
        companies = await hoa_service.list_companies(page=1, page_size=100, fallback=local)

        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []
        for vendor in companies + local:
            vendor_id = vendor.get("id")
            if vendor_id and vendor_id not in seen_ids:
                seen_ids.add(vendor_id)
                merged.append(vendor)

        if query:
            ql = query.lower()
            merged = [vendor for vendor in merged if ql in vendor.get("name", "").lower()]

        return {"total": len(merged), "data": merged}

    async def search(self, query: str) -> dict[str, Any]:
        """Search vendors via HoA with local fallback."""
        if not query.strip():
            return {"total": 0, "data": []}
        local = await self.list_local_vendors()
        companies = await hoa_service.search_companies(query, fallback=local)
        return {"total": len(companies), "data": companies}

    async def create(self, name: str) -> dict[str, Any]:
        """Create a vendor in HoA (or local fallback)."""
        return await hoa_service.create_company(name.strip())
