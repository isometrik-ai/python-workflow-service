"""Work order domain schemas and enums."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse
from app.schemas.contracts import VisitFrequency


class WorkOrderState(str, Enum):
    """Execution lifecycle state of a work order."""

    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class WorkOrderPriority(str, Enum):
    """Relative urgency assigned to a work order."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkOrderSource(str, Enum):
    """Origin that created the work order."""

    CONTRACT = "contract"
    AD_HOC = "ad_hoc"
    RECURRING = "recurring"


class CreateWorkOrderRequest(BaseModel):
    """Request body for creating a work order."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=8000)
    asset_ids: list[str] = Field(default_factory=list)
    contract_id: str | None = None
    vendor_id: str | None = None
    state: WorkOrderState | None = None
    priority: WorkOrderPriority | None = None
    source: WorkOrderSource | None = None
    scheduled_date: date | None = None
    assignee: str | None = Field(None, max_length=255)
    assignee_user_id: str | None = None
    access_notes: str | None = Field(None, max_length=4000)
    form_template_id: str | None = None
    pre_start_form_template_id: str | None = None
    is_recurring: bool = False
    recurring_frequency: VisitFrequency | None = None
    recurring_days: list[str] = Field(default_factory=list)
    recurring_end_date: date | None = None
    recurring_parent_id: str | None = None
    estimated_cost: int | None = Field(None, ge=0)
    line_items: list[Any] = Field(default_factory=list)
    form_values: dict[str, Any] = Field(default_factory=dict)
    pre_start_form_values: dict[str, Any] = Field(default_factory=dict)


class UpdateWorkOrderRequest(BaseModel):
    """Request body for updating a work order."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, max_length=8000)
    asset_ids: list[str] | None = None
    state: WorkOrderState | None = None
    priority: WorkOrderPriority | None = None
    scheduled_date: date | None = None
    vendor_id: str | None = None
    assignee: str | None = Field(None, max_length=255)
    assignee_user_id: str | None = None
    access_notes: str | None = Field(None, max_length=4000)
    form_template_id: str | None = None
    pre_start_form_template_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_cost: int | None = Field(None, ge=0)
    line_items: list[Any] | None = None
    form_values: dict[str, Any] | None = None
    pre_start_form_values: dict[str, Any] | None = None
    invoice_ids: list[str] | None = None
    termination_reason: str | None = Field(None, max_length=2000)
    is_recurring: bool | None = None
    recurring_frequency: VisitFrequency | None = None
    recurring_days: list[str] | None = None
    recurring_end_date: date | None = None


class VendorUpdateWorkOrderRequest(BaseModel):
    """Vendor portal partial update (restricted fields)."""

    model_config = ConfigDict(extra="forbid")

    state: WorkOrderState | None = None
    line_items: list[Any] | None = None
    form_values: dict[str, Any] | None = None
    pre_start_form_values: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class WorkOrderResponse(BaseModel):
    """Work order response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    title: str
    description: str | None = None
    asset_ids: list[str] = Field(default_factory=list)
    contract_id: str | None = None
    vendor_id: str | None = None
    form_template_id: str | None = None
    pre_start_form_template_id: str | None = None
    state: WorkOrderState
    priority: WorkOrderPriority
    source: WorkOrderSource
    scheduled_date: date | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    assignee: str | None = None
    assignee_user_id: str | None = None
    line_items: list[Any] = Field(default_factory=list)
    form_values: dict[str, Any] = Field(default_factory=dict)
    pre_start_form_values: dict[str, Any] = Field(default_factory=dict)
    estimated_cost: int | None = None
    access_notes: str | None = None
    is_recurring: bool = False
    recurring_frequency: VisitFrequency | None = None
    recurring_days: list[str] = Field(default_factory=list)
    recurring_end_date: date | None = None
    recurring_parent_id: str | None = None
    recurring_next_date: date | None = None
    invoice_ids: list[str] = Field(default_factory=list)
    vendor_token_hash: str | None = None
    timeline: list[Any] = Field(default_factory=list)
    termination_reason: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WorkOrderDetailDataResponse(DataResponse[WorkOrderResponse]):
    """Success envelope for a single work order."""


class WorkOrderListDataResponse(ListResponse):
    """Success envelope for paginated work orders."""


class WorkOrderTimelineDataResponse(DataResponse[list[Any]]):
    """Success envelope for work order timeline."""
