"""Tests for enums."""

from app.schemas.common import RecordStatus
from app.schemas.work_orders import WorkOrderSource, WorkOrderState


def test_record_status_values():
    """Test record status values."""
    assert RecordStatus.ACTIVE.value == "active"
    assert RecordStatus.DELETED.value == "deleted"


def test_work_order_state_values():
    """Test work order state values."""
    assert WorkOrderState.UPCOMING.value == "upcoming"
    assert WorkOrderState.COMPLETED.value == "completed"


def test_work_order_source_values():
    """Test work order source values."""
    assert WorkOrderSource.CONTRACT.value == "contract"
    assert WorkOrderSource.AD_HOC.value == "ad_hoc"
