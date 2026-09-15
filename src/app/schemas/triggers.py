"""Integration trigger schemas and enums."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse


class TriggerEntity(str, Enum):
    """Domain entity that can emit webhook trigger events."""

    WORK_ORDER = "work_order"
    CONTRACT = "contract"
    INVOICE = "invoice"
    PAYMENT = "payment"


class TriggerEvent(str, Enum):
    """Lifecycle event that can fire a webhook trigger."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"


class CreateTriggerRequest(BaseModel):
    """Request body for creating a webhook trigger."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    entity: TriggerEntity
    event: TriggerEvent
    webhook_url: str = Field(..., min_length=1, max_length=2000)
    is_active: bool = True
    secret: str | None = Field(None, max_length=500)


class UpdateTriggerRequest(BaseModel):
    """Request body for updating a webhook trigger."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    entity: TriggerEntity | None = None
    event: TriggerEvent | None = None
    webhook_url: str | None = Field(None, min_length=1, max_length=2000)
    is_active: bool | None = None
    secret: str | None = Field(None, max_length=500)


class TriggerResponse(BaseModel):
    """Webhook trigger configuration response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    name: str
    entity: TriggerEntity
    event: TriggerEvent
    is_active: bool = True
    webhook_url: str
    secret: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TriggerListItems(BaseModel):
    """Non-paginated trigger list wrapper."""

    items: list[TriggerResponse] = Field(default_factory=list)


class TriggerListDataResponse(DataResponse[TriggerListItems]):
    """Success envelope for trigger list."""


class TriggerDetailDataResponse(DataResponse[TriggerResponse]):
    """Success envelope for a single trigger."""


class TriggerTestResult(BaseModel):
    """Result of a trigger test delivery."""

    delivered: bool
    status: int | None = None
    error: str | None = None
    duration_ms: int = 0


class TriggerTestDataResponse(DataResponse[TriggerTestResult]):
    """Success envelope for trigger test."""


class SchedulerRunResult(BaseModel):
    """Summary counts from a scheduler run."""

    created: int = 0
    cancelled: int = 0
    skipped: int = 0
    locked: int | None = None


class SchedulerRunDataResponse(DataResponse[SchedulerRunResult]):
    """Success envelope for scheduler run."""
