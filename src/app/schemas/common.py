"""Shared schemas and enums used across work-order domains."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class RecordStatus(str, Enum):
    """Lifecycle status for soft-deleted records."""

    ACTIVE = "active"
    DELETED = "deleted"


class AuditAction(str, Enum):
    """Type of change recorded in an audit event."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"


class AuditSource(str, Enum):
    """Origin system that produced an audit event."""

    FM = "fm"
    VENDOR_PORTAL = "vendor_portal"
    SCHEDULER = "scheduler"
    API = "api"


class ApiKeyScope(BaseModel):
    """Resolved tenant/project scope from API key authentication."""

    tenant_id: str
    project_id: str
    api_key_id: str | None = None
    api_key_name: str | None = None


class TimelineEventRequest(BaseModel):
    """Body for appending a timeline event."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(..., min_length=1, max_length=100)
    note: str | None = Field(None, max_length=4000)
    by: str | None = Field(None, max_length=255)
    from_: str | None = Field(None, alias="from", max_length=128)
    to: str | None = Field(None, max_length=128)
