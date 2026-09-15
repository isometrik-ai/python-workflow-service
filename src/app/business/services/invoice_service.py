"""Vendor invoice business logic."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.events_service import EventsService, diff_records
from app.core.exceptions.http_exceptions import DuplicateValueException, NotFoundException
from app.core.utils.timeline import new_timeline_event
from app.crud.crud_invoices import crud_invoices
from app.crud.crud_work_orders import crud_work_orders
from app.schemas.common import AuditSource
from app.schemas.invoices import InvoiceStatus

_INVOICE_STATUS_TIMELINE_EVENTS = {
    "revision_requested": "revision_requested",
    "approved": "approved",
    "rejected": "rejected",
    "paid": "paid",
}


class InvoiceService:
    """Vendor invoice operations scoped to tenant/project."""

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
        work_order_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated invoices for the tenant/project."""
        return await crud_invoices.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            work_order_id=work_order_id,
            status=status,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one invoice by ID."""
        record = await crud_invoices.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(
        self, data: dict[str, Any], *, source: str = AuditSource.FM.value
    ) -> dict[str, Any]:
        """Create a vendor invoice and emit audit/webhook events."""
        await self._ensure_work_order_exists(data["work_order_id"])
        payload = self._prepare_create_payload(data)
        try:
            record = await crud_invoices.create(
                self.db,
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                data=payload,
            )
        except IntegrityError as exc:
            raise DuplicateValueException(message_key="invoices.errors.duplicate_number") from exc
        await self._events.record_and_dispatch(
            entity="invoice",
            action="created",
            record=record,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            source=source,
        )
        return record

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update an invoice and emit audit/webhook events."""
        before = await self.get(entity_id)
        payload_data = dict(data)
        note = payload_data.pop("note", None)
        payload_data.pop("timeline", None)
        old_status = before.get("status")
        payload = self._prepare_update_payload(payload_data)
        if not payload:
            return before
        try:
            record = await crud_invoices.update(
                self.db,
                tenant_id=self.tenant_id,
                project_id=self.project_id,
                entity_id=entity_id,
                data=payload,
            )
        except IntegrityError as exc:
            raise DuplicateValueException(message_key="invoices.errors.duplicate_number") from exc
        if not record:
            raise NotFoundException(message_key="errors.not_found")

        new_status = record.get("status")
        if old_status and new_status != old_status:
            event_type = _INVOICE_STATUS_TIMELINE_EVENTS.get(str(new_status))
            if not event_type and new_status == InvoiceStatus.SUBMITTED.value:
                event_type = "resubmitted"
            if event_type:
                timeline_event: dict[str, Any] = {"type": event_type}
                if note:
                    timeline_event["note"] = note
                await self.append_timeline(
                    entity_id,
                    event_type=timeline_event["type"],
                    note=timeline_event.get("note"),
                )
                record = await self.get(entity_id)
        await self._events.record_and_dispatch(
            entity="invoice",
            action="updated",
            record=record,
            changes=diff_records(before, record),
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete an invoice and emit audit/webhook events."""
        before = await self.get(entity_id)
        deleted = await crud_invoices.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        await self._events.record_and_dispatch(
            entity="invoice",
            action="deleted",
            record=before,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return entity_id

    async def append_timeline(
        self,
        entity_id: str,
        *,
        event_type: str,
        note: str | None = None,
        by: str | None = None,
    ) -> list[dict[str, Any]]:
        """Append a timeline event to an invoice."""
        timeline = await crud_invoices.append_timeline(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            event={
                "type": event_type,
                "note": note,
                "by": by,
            },
        )
        if timeline is None:
            raise NotFoundException(message_key="errors.not_found")
        return timeline

    async def _ensure_work_order_exists(self, entity_id: str) -> None:
        record = await crud_work_orders.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")

    @staticmethod
    def _prepare_create_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload = dict(data)
        payload["invoice_number"] = payload["invoice_number"].strip()
        payload.setdefault("line_items", [])
        payload.setdefault("document", {})
        payload.setdefault("files", [])
        payload.setdefault("revisions", [])
        payload["currency"] = payload.get("currency") or "INR"
        payload["status"] = _enum_value(payload.get("status"), InvoiceStatus.SUBMITTED)
        if not payload.get("timeline"):
            payload["timeline"] = [new_timeline_event({"type": "submitted"})]
        return payload

    @staticmethod
    def _prepare_update_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if value is None and key not in {"date"}:
                continue
            if key == "invoice_number" and isinstance(value, str):
                payload[key] = value.strip()
            elif isinstance(value, Enum):
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
