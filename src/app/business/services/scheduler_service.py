"""Lazy, idempotent work-order generation from maintenance contracts."""

from __future__ import annotations

import calendar
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.events_service import EventsService
from app.core.utils.timeline import new_timeline_event
from app.core.utils.tokens import generate_vendor_token
from app.crud.crud_contracts import crud_contracts
from app.crud.crud_work_orders import crud_work_orders
from app.schemas.common import AuditSource, RecordStatus
from app.schemas.contracts import ContractStatus
from app.schemas.work_orders import WorkOrderPriority, WorkOrderSource, WorkOrderState

DEFAULT_LEAD_DAYS = 5
RECURRING_LEAD_DAYS = 5
GENERATING_STATUS = ContractStatus.ACTIVE.value
TERMINAL_STATUSES = (ContractStatus.TERMINATED.value, ContractStatus.EXPIRED.value)

DAY_STEPS = {"daily": 1, "weekly": 7, "fortnightly": 14}
MONTH_STEPS = {
    "monthly": 1,
    "quarterly": 3,
    "half_yearly": 6,
    "yearly": 12,
}
WEEKDAY_FREQUENCIES = {"weekly", "fortnightly"}
MONTH_FREQUENCIES = set(MONTH_STEPS)

_MAX_VISITS = 1000
_HORIZON_DAYS = 366 * 5
_SCHEDULER_LOCK_KEY = (824_731, 1)

_WEEKDAY_NAMES = {
    "mon": 1,
    "monday": 1,
    "tue": 2,
    "tuesday": 2,
    "wed": 3,
    "wednesday": 3,
    "thu": 4,
    "thursday": 4,
    "fri": 5,
    "friday": 5,
    "sat": 6,
    "saturday": 6,
    "sun": 7,
    "sunday": 7,
}


def _today() -> date:
    return datetime.now(UTC).date()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_d(value: object | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _add_months(day: date, months: int) -> date:
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def _normalize_days(raw: object, frequency: str) -> list[int]:
    if not raw:
        return []
    out: list[int] = []
    for day_value in raw:
        try:
            out.append(int(day_value))
        except (TypeError, ValueError):
            name = _WEEKDAY_NAMES.get(str(day_value).strip().lower())
            if name:
                out.append(name)
    low, high = (1, 7) if frequency in WEEKDAY_FREQUENCIES else (1, 28)
    return sorted({min(max(value, low), high) for value in out if low <= value <= high})


def next_occurrence(after: date, frequency: str, days: list[int]) -> date:
    """Compute the next recurring visit date after a given anchor."""
    days_n = _normalize_days(days, frequency)
    if frequency in WEEKDAY_FREQUENCIES:
        span = DAY_STEPS.get(frequency, 7)
        if not days_n:
            return after + timedelta(days=span)
        for offset in range(1, span + 1):
            candidate = after + timedelta(days=offset)
            if candidate.isoweekday() in days_n:
                return candidate
        return after + timedelta(days=span)
    months = MONTH_STEPS.get(frequency, 1)
    nxt = _add_months(after, months)
    if not days_n:
        return nxt
    candidate = nxt.replace(day=min(days_n))
    if candidate <= after:
        candidate = _add_months(nxt, 1).replace(day=min(days_n))
    return candidate


def _step(day: date, frequency: str) -> date:
    if frequency in DAY_STEPS:
        return day + timedelta(days=DAY_STEPS[frequency])
    months = MONTH_STEPS.get(frequency, 3)
    return _add_months(day, months)


def _lead_days(contract: dict[str, Any]) -> int:
    raw = contract.get("auto_generate_lead_days")
    if raw is None:
        return DEFAULT_LEAD_DAYS
    return max(0, int(raw))


def _iter_visit_dates(contract: dict[str, Any], today: date):
    start = _parse_d(contract.get("start_date"))
    if not start:
        return
    end = _parse_d(contract.get("end_date"))
    last = _parse_d(contract.get("last_serviced_date"))
    frequency = contract.get("visit_frequency") or "quarterly"

    if last:
        anchor = max(start, last)
        visit = _step(anchor, frequency)
    else:
        visit = start

    horizon = today + timedelta(days=_HORIZON_DAYS)
    for _ in range(_MAX_VISITS):
        if end is not None and visit > end:
            return
        if visit > horizon:
            return
        yield visit
        visit = _step(visit, frequency)


class SchedulerService:
    """Generate due work orders from contracts and recurring templates."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service with a database session."""
        self.db = db

    async def try_advisory_lock(self) -> bool:
        """Try to acquire the scheduler PostgreSQL advisory lock."""
        result = await self.db.execute(
            text("SELECT pg_try_advisory_lock(:a, :b)"),
            {"a": _SCHEDULER_LOCK_KEY[0], "b": _SCHEDULER_LOCK_KEY[1]},
        )
        return bool(result.scalar_one())

    async def release_advisory_lock(self) -> None:
        """Release the scheduler PostgreSQL advisory lock."""
        await self.db.execute(
            text("SELECT pg_advisory_unlock(:a, :b)"),
            {"a": _SCHEDULER_LOCK_KEY[0], "b": _SCHEDULER_LOCK_KEY[1]},
        )

    def _build_work_order(self, contract: dict[str, Any], visit: date, lead: int) -> dict[str, Any]:
        raw_token, token_hash = generate_vendor_token()
        freq = contract.get("visit_frequency") or "quarterly"
        title = f"{freq} visit — {contract['title']} ({visit.isoformat()})"
        return {
            "title": title[:256],
            "description": contract.get("scope_included"),
            "asset_ids": contract.get("asset_ids") or [],
            "contract_id": contract["id"],
            "vendor_id": contract.get("vendor_id"),
            "form_template_id": contract.get("form_template_id"),
            "state": WorkOrderState.UPCOMING.value,
            "priority": WorkOrderPriority.MEDIUM.value,
            "source": WorkOrderSource.CONTRACT.value,
            "scheduled_date": visit,
            "vendor_token_hash": token_hash,
            "timeline": [
                new_timeline_event(
                    {
                        "type": "created",
                        "by": "Scheduler",
                        "note": f"Auto-generated from contract (lead {lead}d); token={raw_token}",
                    }
                )
            ],
        }

    async def _generate_for_contract(
        self,
        contract: dict[str, Any],
        today: date,
    ) -> tuple[int, int, date | None]:
        lead = _lead_days(contract)
        existing = await crud_work_orders.existing_contract_schedule_dates(
            self.db,
            contract_id=contract["id"],
        )
        created = 0
        skipped = 0
        next_future: date | None = None

        for visit in _iter_visit_dates(contract, today):
            if visit > today and next_future is None:
                next_future = visit
            if visit > today + timedelta(days=lead):
                break
            if visit.isoformat() in existing:
                skipped += 1
                continue
            work_order_data = self._build_work_order(contract, visit, lead)
            record = await crud_work_orders.create(
                self.db,
                tenant_id=contract["tenant_id"],
                project_id=contract["project_id"],
                data=work_order_data,
            )
            await EventsService(self.db).record_and_dispatch(
                entity="work_order",
                action="created",
                record=record,
                tenant_id=contract["tenant_id"],
                project_id=contract["project_id"],
                source=AuditSource.SCHEDULER.value,
            )
            created += 1

        await crud_contracts.update_next_visit_date(
            self.db,
            contract_id=contract["id"],
            next_visit_date=next_future,
        )
        return created, skipped, next_future

    async def _cancel_pending(self, contract: dict[str, Any], _note: str = "") -> int:
        return await crud_work_orders.cancel_contract_work_orders(
            self.db,
            contract_id=contract["id"],
        )

    async def recompute_contract(
        self,
        contract: dict[str, Any],
        *,
        terms_changed: bool = False,
        status_changed: bool = False,
        terminal_note: str = "Cancelled — contract terminated",
    ) -> dict[str, int]:
        """Regenerate or cancel work orders after contract changes."""
        status = (contract.get("status") or "").lower()
        if (
            contract.get("record_status") == RecordStatus.DELETED.value
            or status in TERMINAL_STATUSES
        ):
            cancelled = await self._cancel_pending(contract, terminal_note)
            return {"cancelled": cancelled}

        if status != GENERATING_STATUS:
            return {"cancelled": 0}

        if terms_changed or status_changed:
            await self._cancel_pending(contract, "Cancelled — contract terms changed")
        created, skipped, _ = await self._generate_for_contract(contract, _today())
        return {"created": created, "cancelled": 0, "skipped": skipped}

    async def generate_recurring_work_orders(self, tenant_id: str | None = None) -> dict[str, int]:
        """Create upcoming instances from recurring work-order templates."""
        counts = {"created": 0, "skipped": 0}
        today = _today()
        templates = await crud_work_orders.list_recurring_templates(self.db, tenant_id=tenant_id)

        for template in templates:
            try:
                existing = await crud_work_orders.recurring_child_dates(
                    self.db,
                    template_id=template["id"],
                )
                last_child = max((_parse_d(d) for d in existing), default=None)
                anchor = (
                    _parse_d(template.get("scheduled_date"))
                    or _parse_d(template.get("started_at"))
                    or today
                )
                after = max(anchor, last_child or today)
                next_date = next_occurrence(
                    after,
                    template.get("recurring_frequency") or "weekly",
                    template.get("recurring_days") or [],
                )
                end = _parse_d(template.get("recurring_end_date"))
                if end and next_date > end:
                    counts["skipped"] += 1
                elif next_date.isoformat() in existing:
                    counts["skipped"] += 1
                elif next_date - timedelta(days=RECURRING_LEAD_DAYS) <= today:
                    raw_token, token_hash = generate_vendor_token()
                    record = await crud_work_orders.create(
                        self.db,
                        tenant_id=template["tenant_id"],
                        project_id=template["project_id"],
                        data={
                            "title": f"{template['title']} — {next_date.isoformat()}"[:256],
                            "description": template.get("description"),
                            "asset_ids": template.get("asset_ids") or [],
                            "contract_id": template.get("contract_id"),
                            "vendor_id": template.get("vendor_id"),
                            "form_template_id": template.get("form_template_id"),
                            "state": WorkOrderState.UPCOMING.value,
                            "priority": template.get("priority") or WorkOrderPriority.MEDIUM.value,
                            "source": template.get("source") or WorkOrderSource.AD_HOC.value,
                            "scheduled_date": next_date,
                            "assignee": template.get("assignee"),
                            "access_notes": template.get("access_notes"),
                            "is_recurring": False,
                            "recurring_parent_id": template["id"],
                            "vendor_token_hash": token_hash,
                            "timeline": [
                                new_timeline_event(
                                    {
                                        "type": "created",
                                        "by": "Scheduler",
                                        "note": f"Recurring instance; token={raw_token}",
                                    }
                                )
                            ],
                        },
                    )
                    await EventsService(self.db).record_and_dispatch(
                        entity="work_order",
                        action="created",
                        record=record,
                        tenant_id=template["tenant_id"],
                        project_id=template["project_id"],
                        source=AuditSource.SCHEDULER.value,
                    )
                    counts["created"] += 1
                await crud_work_orders.update_recurring_next_date(
                    self.db,
                    work_order_id=template["id"],
                    next_date=next_date if not (end and next_date > end) else None,
                )
            except Exception:
                continue

        return counts

    async def generate_due_work_orders(self, tenant_id: str | None = None) -> dict[str, int]:
        """Generate due contract and recurring work orders."""
        counts = {"created": 0, "cancelled": 0, "skipped": 0}
        today = _today()
        contracts = await crud_contracts.list_active_for_scheduler(self.db, tenant_id=tenant_id)

        for contract in contracts:
            status = (contract.get("status") or "").lower()
            if status in TERMINAL_STATUSES:
                counts["cancelled"] += await self._cancel_pending(contract)
                continue
            if status != GENERATING_STATUS:
                continue
            created, skipped, _ = await self._generate_for_contract(contract, today)
            counts["created"] += created
            counts["skipped"] += skipped

        recurring = await self.generate_recurring_work_orders(tenant_id)
        counts["created"] += recurring["created"]
        counts["skipped"] += recurring["skipped"]
        return counts

    async def run_once(self, tenant_id: str | None = None) -> dict[str, int]:
        """Run one scheduler pass under advisory lock."""
        if not await self.try_advisory_lock():
            return {"created": 0, "cancelled": 0, "skipped": 0, "locked": 1}
        try:
            return await self.generate_due_work_orders(tenant_id)
        finally:
            await self.release_advisory_lock()
