"""PDF template schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse


class CreatePdfTemplateRequest(BaseModel):
    """Request body for creating a PDF template."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=256)
    doc_type: str = Field(default="work_order", pattern="^(work_order|payment_receipt)$")
    is_default: bool = False
    base_pdf: str | None = None
    schemas: list[Any] = Field(default_factory=list)


class UpdatePdfTemplateRequest(BaseModel):
    """Request body for updating a PDF template."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=256)
    doc_type: str | None = Field(None, pattern="^(work_order|payment_receipt)$")
    is_default: bool | None = None
    base_pdf: str | None = None
    schemas: list[Any] | None = None


class PdfTemplateResponse(BaseModel):
    """PDF template response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    name: str
    doc_type: str
    is_default: bool
    base_pdf: str | None = None
    schemas: list[Any] = Field(default_factory=list)
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PdfTemplateDetailDataResponse(DataResponse[PdfTemplateResponse]):
    """Success envelope for a single PDF template."""


class PdfTemplateListDataResponse(ListResponse):
    """Success envelope for PDF template list."""


__all__ = [
    "CreatePdfTemplateRequest",
    "DeleteIdDataResponse",
    "DeleteIdResponse",
    "PdfTemplateDetailDataResponse",
    "PdfTemplateListDataResponse",
    "PdfTemplateResponse",
    "UpdatePdfTemplateRequest",
]
