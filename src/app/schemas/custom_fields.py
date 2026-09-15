"""Custom field definition schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse


class CreateCustomFieldRequest(BaseModel):
    """Request body for creating a custom field."""

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(..., min_length=1, max_length=128)
    field_key: str = Field(..., min_length=1, max_length=128)
    field_type: str = Field(..., min_length=1, max_length=32)
    type_config: dict[str, Any] = Field(default_factory=dict)
    is_required: bool = False
    is_active: bool = True
    sort_order: int = 0
    show_on_create: bool = True
    show_on_detail: bool = True
    scope: str = Field(default="global", pattern="^(global|category)$")
    category_id: str | None = None


class UpdateCustomFieldRequest(BaseModel):
    """Request body for updating a custom field."""

    model_config = ConfigDict(extra="forbid")

    field_name: str | None = Field(None, min_length=1, max_length=128)
    field_key: str | None = Field(None, min_length=1, max_length=128)
    field_type: str | None = Field(None, min_length=1, max_length=32)
    type_config: dict[str, Any] | None = None
    is_required: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    show_on_create: bool | None = None
    show_on_detail: bool | None = None
    scope: str | None = Field(None, pattern="^(global|category)$")
    category_id: str | None = None


class CustomFieldResponse(BaseModel):
    """Custom field response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    field_name: str
    field_key: str
    field_type: str
    type_config: dict[str, Any] = Field(default_factory=dict)
    is_required: bool
    is_active: bool
    sort_order: int
    show_on_create: bool
    show_on_detail: bool
    scope: str
    category_id: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CustomFieldDetailDataResponse(DataResponse[CustomFieldResponse]):
    """Success envelope for a single custom field."""


class CustomFieldListDataResponse(ListResponse):
    """Success envelope for paginated custom fields."""


class DeleteCustomFieldResponse(BaseModel):
    """Delete confirmation payload."""

    id: str


class DeleteCustomFieldDataResponse(DataResponse[DeleteCustomFieldResponse]):
    """Success envelope for custom field delete operations."""
