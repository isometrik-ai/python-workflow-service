"""Vendor portal token authentication."""

from __future__ import annotations

from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.work_order_service import WorkOrderService
from app.core.db.postgres.database import async_get_db
from app.core.utils.header_validators import HeaderVendorAuth, get_header_vendor_auth


async def get_work_order_from_vendor_token(
    headers: HeaderVendorAuth = Depends(get_header_vendor_auth),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, Any]:
    """Load a work order using the vendor portal token from request headers."""
    service = WorkOrderService(db=db)
    return await service.get_by_vendor_token(headers.x_vendor_token)
