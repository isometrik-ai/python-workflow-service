"""Work order business logic."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.events_service import EventsService, diff_records
from app.core.constants.status_codes import CustomStatusCode
from app.core.exceptions.http_exceptions import NotFoundException, ValidationException
from app.core.utils.tokens import generate_vendor_token, hash_vendor_token
from app.crud.crud_assets import crud_assets
from app.crud.crud_contracts import crud_contracts
from app.crud.crud_form_templates import crud_form_templates
from app.crud.crud_work_orders import crud_work_orders
from app.schemas.common import AuditSource
from app.schemas.work_orders import WorkOrderPriority, WorkOrderSource, WorkOrderState

RECURRING_FIELDS = frozenset(
    {
        "is_recurring",
        "recurring_frequency",
        "recurring_days",
        "scheduled_date",
        "recurring_end_date",
    }
)


class WorkOrderService:
    """Work order operations for staff and vendor flows."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        """Initialize the service with database session and optional scope."""
        self.db = db
        self.tenant_id = tenant_id
        self.project_id = project_id
        self._events = EventsService(db)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        state: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated work orders for the tenant/project."""
        return await crud_work_orders.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            state=state,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one work order by ID."""
        record = await crud_work_orders.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a work order and emit audit/webhook events."""
        await self._validate_references(data)
        payload = self._prepare_create_payload(data)
        if not payload.get("vendor_token_hash"):
            raw, token_hash = generate_vendor_token()
            payload["vendor_token_hash"] = token_hash
            payload["timeline"] = [
                {"type": "created", "note": f"Vendor token issued: {raw}"},
            ]
        record = await crud_work_orders.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            data=payload,
        )
        await self._events.record_and_dispatch(
            entity="work_order",
            action="created",
            record=record,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return record

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a work order and reconcile recurring children."""
        before = await self.get(entity_id)
        payload_data = dict(data)
        payload_data.pop("timeline", None)
        await self._validate_references(payload_data)
        payload = self._prepare_update_payload(payload_data)
        if not payload:
            return before
        was_template = bool(before.get("is_recurring"))
        change_keys = set(payload_data.keys())
        recurring_changed = was_template and any(key in change_keys for key in RECURRING_FIELDS)
        terminating = _is_terminated(payload_data.get("state"))
        record = await crud_work_orders.update(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            data=payload,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        if record:
            if was_template and recurring_changed and record.get("is_recurring"):
                await crud_work_orders.cancel_recurring_children(
                    self.db,
                    template_id=entity_id,
                    note="Recurring schedule changed",
                )
            elif was_template and payload_data.get("is_recurring") is False:
                await crud_work_orders.cancel_recurring_children(
                    self.db,
                    template_id=entity_id,
                    note="Recurring schedule disabled",
                )
            elif was_template and terminating:
                await crud_work_orders.cancel_recurring_children(
                    self.db,
                    template_id=entity_id,
                    note="Cancelled — template terminated",
                )
        await self._events.record_and_dispatch(
            entity="work_order",
            action="updated",
            record=record,
            changes=diff_records(before, record),
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete a work order and cancel recurring children."""
        before = await self.get(entity_id)
        if before.get("is_recurring"):
            await crud_work_orders.cancel_recurring_children(
                self.db,
                template_id=entity_id,
                note="Cancelled — template deleted",
            )
        deleted = await crud_work_orders.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        await self._events.record_and_dispatch(
            entity="work_order",
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
        from_: str | None = None,
        to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Append a timeline event to a work order."""
        event: dict[str, Any] = {"type": event_type}
        if note is not None:
            event["note"] = note
        if by is not None:
            event["by"] = by
        if from_ is not None:
            event["from"] = from_
        if to is not None:
            event["to"] = to
        timeline = await crud_work_orders.append_timeline(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            event=event,
        )
        if timeline is None:
            raise NotFoundException(message_key="errors.not_found")
        record = await self.get(entity_id)
        await self._events.record_and_dispatch(
            entity="work_order",
            action="updated",
            record=record,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return timeline

    async def get_by_vendor_token(self, vendor_token: str) -> dict[str, Any]:
        """Return a work order resolved from a vendor token."""
        if not vendor_token or len(vendor_token) < 16:
            raise ValidationException(
                message_key="auth.errors.unauthorized",
                custom_code=CustomStatusCode.UNAUTHORIZED,
            )
        work_order = await crud_work_orders.get_by_vendor_token_hash(
            self.db,
            hash_vendor_token(vendor_token),
        )
        if not work_order:
            raise ValidationException(
                message_key="auth.errors.unauthorized",
                custom_code=CustomStatusCode.UNAUTHORIZED,
            )
        return work_order

    async def vendor_update(
        self,
        work_order: dict[str, Any],
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Update vendor-scoped fields on a work order."""
        payload_data = dict(data)
        payload_data.pop("timeline", None)
        payload = self._prepare_update_payload(payload_data)
        if not payload:
            return work_order
        before = dict(work_order)
        record = await crud_work_orders.update(
            self.db,
            tenant_id=work_order["tenant_id"],
            project_id=work_order["project_id"],
            entity_id=work_order["id"],
            data=payload,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        await self._events.record_and_dispatch(
            entity="work_order",
            action="updated",
            record=record,
            changes=diff_records(before, record),
            tenant_id=work_order["tenant_id"],
            project_id=work_order["project_id"],
            source=AuditSource.VENDOR_PORTAL.value,
        )
        return record

    async def _validate_references(self, data: dict[str, Any]) -> None:
        asset_ids = data.get("asset_ids")
        if asset_ids:
            for asset_id in asset_ids:
                await self._ensure_asset_exists(asset_id)
        contract_id = data.get("contract_id")
        if contract_id:
            await self._ensure_contract_exists(contract_id)
        for key in ("form_template_id", "pre_start_form_template_id"):
            template_id = data.get(key)
            if template_id:
                await self._ensure_form_template_exists(template_id)

    async def _ensure_asset_exists(self, entity_id: str) -> None:
        record = await crud_assets.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")

    async def _ensure_contract_exists(self, entity_id: str) -> None:
        record = await crud_contracts.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")

    async def _ensure_form_template_exists(self, entity_id: str) -> None:
        record = await crud_form_templates.get_by_id(
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
        payload["title"] = payload["title"].strip()
        payload.setdefault("asset_ids", [])
        payload.setdefault("line_items", [])
        payload.setdefault("form_values", {})
        payload.setdefault("pre_start_form_values", {})
        payload.setdefault("recurring_days", [])
        payload["state"] = _enum_value(payload.get("state"), WorkOrderState.UPCOMING)
        payload["priority"] = _enum_value(payload.get("priority"), WorkOrderPriority.MEDIUM)
        payload["source"] = _enum_value(payload.get("source"), WorkOrderSource.AD_HOC)
        if payload.get("recurring_frequency") is not None:
            payload["recurring_frequency"] = _enum_value(payload["recurring_frequency"], None)
        return payload

    @staticmethod
    def _prepare_update_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if value is None and key not in {
                "description",
                "scheduled_date",
                "started_at",
                "completed_at",
                "recurring_end_date",
            }:
                continue
            if key == "title" and isinstance(value, str):
                payload[key] = value.strip()
            elif isinstance(value, Enum):
                payload[key] = value.value
            else:
                payload[key] = value
        return payload


def _enum_value(value: Any, default: Enum | None) -> str | None:
    if value is None:
        return default.value if default is not None else None
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _is_terminated(state: Any) -> bool:
    if state is None:
        return False
    if isinstance(state, WorkOrderState):
        return state == WorkOrderState.TERMINATED
    return str(state) == WorkOrderState.TERMINATED.value
