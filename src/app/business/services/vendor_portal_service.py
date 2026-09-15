"""Vendor portal business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.invoice_service import InvoiceService
from app.business.services.work_order_service import WorkOrderService
from app.core.constants.status_codes import CustomStatusCode
from app.core.exceptions.http_exceptions import ValidationException
from app.schemas.common import AuditSource

VENDOR_WORK_ORDER_FIELDS = frozenset(
    {
        "state",
        "line_items",
        "form_values",
        "pre_start_form_values",
        "started_at",
        "completed_at",
    }
)


class VendorPortalService:
    """Token-scoped vendor portal operations."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db
        self._work_orders = WorkOrderService(db=db)

    async def get_work_order(self, vendor_token: str) -> dict[str, Any]:
        """Return a work order accessible via vendor token."""
        return await self._work_orders.get_by_vendor_token(vendor_token)

    async def update_work_order(
        self,
        work_order: dict[str, Any],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update vendor-allowed fields on a work order."""
        allowed = {key: value for key, value in data.items() if key in VENDOR_WORK_ORDER_FIELDS}
        return await self._work_orders.vendor_update(work_order, allowed)

    async def submit_invoice(
        self,
        work_order: dict[str, Any],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit a vendor invoice for a work order."""
        invoice_service = InvoiceService(
            db=self.db,
            tenant_id=work_order["tenant_id"],
            project_id=work_order["project_id"],
        )
        payload = {
            **data,
            "work_order_id": work_order["id"],
            "vendor_id": work_order.get("vendor_id") or data.get("vendor_id"),
        }
        if not payload.get("vendor_id"):
            raise ValidationException(
                message_key="errors.validation",
                custom_code=CustomStatusCode.VALIDATION_ERROR,
                params={"message": "vendor_id is required"},
            )
        return await invoice_service.create(payload, source=AuditSource.VENDOR_PORTAL.value)

    async def list_invoices(
        self,
        work_order: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], int]:
        """Return invoices linked to a vendor work order."""
        invoice_service = InvoiceService(
            db=self.db,
            tenant_id=work_order["tenant_id"],
            project_id=work_order["project_id"],
        )
        return await invoice_service.list(work_order_id=work_order["id"])
