"""Audit and webhook delivery log schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import ListResponse
from app.schemas.common import AuditAction, AuditSource
from app.schemas.triggers import TriggerEntity


class AuditEventResponse(BaseModel):
    """Audit event response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    entity: TriggerEntity
    entity_id: str
    entity_label: str | None = None
    action: AuditAction
    actor: str | None = None
    source: AuditSource
    changes: list[Any] = Field(default_factory=list)
    snapshot: dict[str, Any] = Field(default_factory=dict)
    at: datetime


class AuditEventListDataResponse(ListResponse):
    """Success envelope for paginated audit events."""


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery log response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    trigger_id: str | None = None
    entity: TriggerEntity | None = None
    entity_id: str | None = None
    event: str
    request_payload: dict[str, Any] = Field(default_factory=dict)
    response_status: int | None = None
    error: str | None = None
    attempt: int = 1
    duration_ms: int = 0
    delivered: bool = False
    created_at: datetime


class WebhookDeliveryListDataResponse(ListResponse):
    """Success envelope for paginated webhook deliveries."""


class ApiCallLogResponse(BaseModel):
    """API call log response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    at: datetime
    method: str
    path: str
    status_code: int
    duration_ms: int = 0
    source: str | None = None
    request_body: dict[str, Any] = Field(default_factory=dict)
    response_body: dict[str, Any] = Field(default_factory=dict)


class ApiCallLogListDataResponse(ListResponse):
    """Success envelope for paginated API call logs."""
