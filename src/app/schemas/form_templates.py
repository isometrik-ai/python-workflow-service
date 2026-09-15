"""Form template request/response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse


class CreateFormTemplateRequest(BaseModel):
    """Request body for creating a form template."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    schema: dict[str, Any] = Field(default_factory=dict)


class UpdateFormTemplateRequest(BaseModel):
    """Request body for updating a form template."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    schema: dict[str, Any] | None = None


class FormTemplateResponse(BaseModel):
    """Form template metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    name: str
    description: str = ""
    schema: dict[str, Any] = Field(default_factory=dict)
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FormTemplateDetailDataResponse(DataResponse[FormTemplateResponse]):
    """Success envelope for a single form template."""


class FormTemplateListDataResponse(ListResponse):
    """Success envelope for paginated form templates."""
