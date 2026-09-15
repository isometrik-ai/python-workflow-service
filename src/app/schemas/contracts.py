"""Contract domain schemas and enums."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse


class ContractStatus(str, Enum):
    """Lifecycle status of a maintenance contract."""

    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    PAUSED = "paused"


class VisitFrequency(str, Enum):
    """Scheduled visit cadence for contract work orders."""

    DAILY = "daily"
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    YEARLY = "yearly"


class PaymentFrequency(str, Enum):
    """Billing cadence defined on a maintenance contract."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    HALF_YEARLY = "half_yearly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


class CreateContractRequest(BaseModel):
    """Request body for creating a maintenance contract."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=500)
    vendor_id: str
    start_date: date
    asset_ids: list[str] = Field(default_factory=list)
    end_date: date | None = None
    visit_frequency: VisitFrequency | None = None
    payment_frequency: PaymentFrequency | None = None
    value: int | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=10)
    status: ContractStatus | None = None
    next_visit_date: date | None = None
    last_serviced_date: date | None = None
    auto_generate_lead_days: int | None = Field(None, ge=0, le=365)
    scope_included: str | None = Field(None, max_length=8000)
    scope_excluded: str | None = Field(None, max_length=8000)
    form_template_id: str | None = None
    pre_start_form_template_id: str | None = None
    documents: list[str] = Field(default_factory=list)


class UpdateContractRequest(BaseModel):
    """Request body for updating a maintenance contract."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=500)
    vendor_id: str | None = None
    asset_ids: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    visit_frequency: VisitFrequency | None = None
    payment_frequency: PaymentFrequency | None = None
    value: int | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=10)
    status: ContractStatus | None = None
    next_visit_date: date | None = None
    last_serviced_date: date | None = None
    auto_generate_lead_days: int | None = Field(None, ge=0, le=365)
    scope_included: str | None = Field(None, max_length=8000)
    scope_excluded: str | None = Field(None, max_length=8000)
    form_template_id: str | None = None
    pre_start_form_template_id: str | None = None
    documents: list[str] | None = None
    termination_reason: str | None = Field(None, max_length=2000)


class ContractResponse(BaseModel):
    """Maintenance contract response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    title: str
    vendor_id: str
    asset_ids: list[str] = Field(default_factory=list)
    start_date: date
    end_date: date | None = None
    visit_frequency: VisitFrequency
    payment_frequency: PaymentFrequency
    value: int | None = None
    currency: str = "INR"
    status: ContractStatus
    next_visit_date: date | None = None
    last_serviced_date: date | None = None
    auto_generate_lead_days: int | None = None
    scope_included: str | None = None
    scope_excluded: str | None = None
    form_template_id: str | None = None
    pre_start_form_template_id: str | None = None
    documents: list[str] = Field(default_factory=list)
    termination_reason: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ContractDetailDataResponse(DataResponse[ContractResponse]):
    """Success envelope for a single contract."""


class ContractListDataResponse(ListResponse):
    """Success envelope for paginated contracts."""
