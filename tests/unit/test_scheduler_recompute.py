"""Tests for scheduler recompute."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.business.services.scheduler_service import SchedulerService
from app.schemas.common import RecordStatus
from app.schemas.contracts import ContractStatus


@pytest.fixture
def db():
    """Db."""
    return MagicMock()


@pytest.fixture
def service(db):
    """Service."""
    return SchedulerService(db)


def _contract(**overrides):
    payload = {
        "id": "contract_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "title": "HVAC Annual",
        "status": ContractStatus.ACTIVE.value,
        "record_status": RecordStatus.ACTIVE.value,
        "start_date": date(2026, 1, 1),
        "visit_frequency": "monthly",
        "auto_generate_lead_days": 5,
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_recompute_contract_cancels_terminal(service):
    """Test recompute contract cancels terminal."""
    contract = _contract(status=ContractStatus.TERMINATED.value)
    service._cancel_pending = AsyncMock(return_value=2)

    result = await service.recompute_contract(contract)

    assert result == {"cancelled": 2}
    service._cancel_pending.assert_awaited_once()


@pytest.mark.asyncio
async def test_recompute_contract_regenerates_on_terms_change(service):
    """Test recompute contract regenerates on terms change."""
    contract = _contract()
    service._cancel_pending = AsyncMock(return_value=1)
    service._generate_for_contract = AsyncMock(return_value=(3, 0, date(2026, 2, 1)))

    result = await service.recompute_contract(contract, terms_changed=True)

    assert result == {"created": 3, "cancelled": 0, "skipped": 0}
    service._cancel_pending.assert_awaited_once()
    service._generate_for_contract.assert_awaited_once()


@pytest.mark.asyncio
async def test_recompute_contract_skips_non_active(service):
    """Test recompute contract skips non active."""
    contract = _contract(status=ContractStatus.PAUSED.value)

    result = await service.recompute_contract(contract)

    assert result == {"cancelled": 0}


@pytest.mark.asyncio
async def test_cancel_recurring_children_updates_upcoming_rows():
    """Test cancel recurring children updates upcoming rows."""
    from app.crud.crud_work_orders import crud_work_orders

    db = MagicMock()
    child = MagicMock()
    child.id = "work_order_child1"
    child.timeline = []

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [child]
    db.execute = AsyncMock(return_value=execute_result)

    count = await crud_work_orders.cancel_recurring_children(
        db,
        template_id="work_order_template1",
        note="Recurring schedule changed",
    )

    assert count == 1
    assert db.execute.await_count == 2
