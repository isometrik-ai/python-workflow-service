"""Maintenance contract business logic."""

from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.events_service import EventsService, diff_records
from app.business.services.scheduler_service import SchedulerService
from app.core.exceptions.http_exceptions import NotFoundException
from app.crud.crud_assets import crud_assets
from app.crud.crud_contracts import crud_contracts
from app.crud.crud_form_templates import crud_form_templates
from app.schemas.common import RecordStatus
from app.schemas.contracts import ContractStatus, PaymentFrequency, VisitFrequency


class ContractService:
    """Maintenance contract operations scoped to tenant/project."""

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
        self._scheduler = SchedulerService(db)

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated maintenance contracts for the tenant/project."""
        return await crud_contracts.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            status=status,
        )

    async def get(self, entity_id: str) -> dict[str, Any]:
        """Return one maintenance contract by ID."""
        record = await crud_contracts.get_by_id(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        return record

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Create a maintenance contract and schedule initial work orders."""
        await self._validate_references(data)
        payload = self._prepare_create_payload(data)
        record = await crud_contracts.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            data=payload,
        )
        await self._events.record_and_dispatch(
            entity="contract",
            action="created",
            record=record,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        await self._scheduler.recompute_contract(record)
        return record

    async def update(self, entity_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Update a maintenance contract and recompute scheduled work orders."""
        before = await self.get(entity_id)
        await self._validate_references(data)
        payload = self._prepare_update_payload(data)
        if not payload:
            return before
        record = await crud_contracts.update(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
            data=payload,
        )
        if not record:
            raise NotFoundException(message_key="errors.not_found")
        await self._events.record_and_dispatch(
            entity="contract",
            action="updated",
            record=record,
            changes=diff_records(before, record),
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        terms_changed = any(
            before.get(key) != record.get(key)
            for key in (
                "start_date",
                "end_date",
                "visit_frequency",
                "last_serviced_date",
                "auto_generate_lead_days",
                "asset_ids",
            )
        )
        status_changed = before.get("status") != record.get("status")
        await self._scheduler.recompute_contract(
            record,
            terms_changed=terms_changed,
            status_changed=status_changed,
        )
        return record

    async def delete(self, entity_id: str) -> str:
        """Soft-delete a maintenance contract and cancel pending work orders."""
        before = await self.get(entity_id)
        deleted = await crud_contracts.soft_delete(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            entity_id=entity_id,
        )
        if not deleted:
            raise NotFoundException(message_key="errors.not_found")
        before["record_status"] = RecordStatus.DELETED.value
        await self._scheduler.recompute_contract(before, status_changed=True)
        await self._events.record_and_dispatch(
            entity="contract",
            action="deleted",
            record=before,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
        )
        return entity_id

    async def _validate_references(self, data: dict[str, Any]) -> None:
        asset_ids = data.get("asset_ids")
        if asset_ids:
            for asset_id in asset_ids:
                await self._ensure_asset_exists(asset_id)
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
        payload.setdefault("documents", [])
        payload["visit_frequency"] = _enum_value(
            payload.get("visit_frequency"), VisitFrequency.QUARTERLY
        )
        payload["payment_frequency"] = _enum_value(
            payload.get("payment_frequency"), PaymentFrequency.QUARTERLY
        )
        payload["currency"] = payload.get("currency") or "INR"
        payload["status"] = _enum_value(payload.get("status"), ContractStatus.ACTIVE)
        return payload

    @staticmethod
    def _prepare_update_payload(data: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        for key, value in data.items():
            if value is None and key not in {"end_date", "next_visit_date", "last_serviced_date"}:
                continue
            if key == "title" and isinstance(value, str):
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
