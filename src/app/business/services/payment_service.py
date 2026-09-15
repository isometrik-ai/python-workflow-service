"""Payment business logic."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.events_service import EventsService, diff_records
from app.business.services.invoice_service import InvoiceService
from app.business.services.work_order_service import WorkOrderService
from app.core.exceptions.http_exceptions import NotFoundException
from app.crud.crud_invoices import crud_invoices
from app.crud.crud_payments import crud_payments
from app.crud.crud_work_orders import crud_work_orders
from app.schemas.invoices import InvoiceStatus
from app.schemas.payments import PaymentMethod, PaymentStatus


class PaymentService:
    """Payment operations scoped to tenant/project."""

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
        self._events = EventsService(db)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        invoice_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated payments for the tenant/project."""
        return await crud_payments.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            invoice_id=invoice_id,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one payment by ID."""
        record = await crud_payments.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a payment and settle the linked invoice when completed."""
        await self._validate_references(data)
        payload = self._prepare_create_payload(data)
        record = await crud_payments.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            data=payload,
        )
        await self._events.record_and_dispatch(
            entity="payment",
            action="created",
            record=record,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        if record.get("invoice_id") and (record.get("status") or PaymentStatus.COMPLETED.value) == (
            PaymentStatus.COMPLETED.value
        ):
            await self._settle_linked_invoice(record)
        return record

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing payment."""
        before = await self.get(entity_id)
        payload = self._prepare_update_payload(data)
        if not payload:
            return before
        record = await crud_payments.update(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            data=payload,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        await self._events.record_and_dispatch(
            entity="payment",
            action="updated",
            record=record,
            changes=diff_records(before, record),
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete a payment."""
        before = await self.get(entity_id)
        deleted = await crud_payments.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        await self._events.record_and_dispatch(
            entity="payment",
            action="deleted",
            record=before,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return entity_id

    async def _validate_references(self, data: dict[str, Any]) -> None:
        invoice_id = data.get("invoice_id")
        if invoice_id:
            await self._ensure_invoice_exists(invoice_id)
        work_order_id = data.get("work_order_id")
        if work_order_id:
            await self._ensure_work_order_exists(work_order_id)

    async def _ensure_invoice_exists(self, entity_id: str) -> None:
        record = await crud_invoices.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")

    async def _ensure_work_order_exists(self, entity_id: str) -> None:
        record = await crud_work_orders.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")

    async def _settle_linked_invoice(self, payment: dict[str, Any]) -> None:
        invoice_id = payment["invoice_id"]
        invoice = await crud_invoices.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=invoice_id,
        )
        if not invoice or invoice.get("status") == InvoiceStatus.PAID.value:
            return

        note = self._payment_timeline_note(
            amount_minor=payment.get("amount"),
            currency=payment.get("currency") or invoice.get("currency") or "INR",
            invoice_number=invoice.get("invoice_number", "invoice"),
            reference=payment.get("reference"),
        )
        invoice_service = InvoiceService(
            db=self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        await invoice_service.update(
            invoice_id,
            {
                "status": InvoiceStatus.PAID.value,
                "payment_id": payment["id"],
                "note": note,
            },
        )

        work_order_id = invoice.get("work_order_id") or payment.get("work_order_id")
        if work_order_id:
            work_order_service = WorkOrderService(
                db=self.db,
                tenant_id=self.tenant_id,
                project_id=self.project_id,
            )
            await work_order_service.append_timeline(
                work_order_id,
                event_type="payment_released",
                note=note,
            )

    @staticmethod
    def _payment_timeline_note(
        *,
        amount_minor: int | None,
        currency: str,
        invoice_number: str,
        reference: str | None,
    ) -> str:
        if amount_minor is not None:
            major = amount_minor / 100
            amount_text = f"₹{major:,.2f}" if currency == "INR" else f"{currency} {major:,.2f}"
            text = f"{amount_text} against {invoice_number}"
        else:
            text = f"Payment recorded against {invoice_number}"
        if reference:
            text = f"{text} · Ref {reference}"
        return text

    @staticmethod
    def _prepare_create_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload["currency"] = payload.get("currency") or "INR"
        payload["method"] = _enum_value(payload.get("method"), PaymentMethod.BANK_TRANSFER)
        payload["status"] = _enum_value(payload.get("status"), PaymentStatus.COMPLETED)
        return payload

    @staticmethod
    def _prepare_update_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if value is None and key not in {"date", "reference", "receipt", "notes"}:
                continue
            if isinstance(value, Enum):
                payload[key] = value.value
            else:
                payload[key] = value
        return payload


def _enum_value(value: Any, default: Enum) -> str:
    if value is None:
        return default.value
    if isinstance(value, Enum):
        return value.value
    return str(value)
