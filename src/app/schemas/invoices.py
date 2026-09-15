"""Invoice domain schemas and enums."""

from datetime import date as DateType
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse


class InvoiceStatus(str, Enum):
    """Approval and payment lifecycle status of a vendor invoice."""

    SUBMITTED = "submitted"
    REVISION_REQUESTED = "revision_requested"
    RESUBMITTED = "resubmitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class CreateInvoiceRequest(BaseModel):
    """Request body for creating a vendor invoice."""

    model_config = ConfigDict(extra="forbid")

    work_order_id: str
    vendor_id: str
    invoice_number: str = Field(..., min_length=1, max_length=100)
    date: DateType | None = None
    line_items: list[Any] = Field(default_factory=list)
    subtotal: int = Field(default=0, ge=0)
    tax: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    currency: str | None = Field(None, max_length=10)
    status: InvoiceStatus | None = None
    document: dict[str, Any] = Field(default_factory=dict)
    files: list[Any] = Field(default_factory=list)
    timeline: list[Any] = Field(default_factory=list)
    revisions: list[Any] = Field(default_factory=list)


class UpdateInvoiceRequest(BaseModel):
    """Request body for updating a vendor invoice."""

    model_config = ConfigDict(extra="forbid")

    invoice_number: str | None = Field(None, min_length=1, max_length=100)
    date: DateType | None = None
    line_items: list[Any] | None = None
    subtotal: int | None = Field(None, ge=0)
    tax: int | None = Field(None, ge=0)
    total: int | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=10)
    status: InvoiceStatus | None = None
    document: dict[str, Any] | None = None
    files: list[Any] | None = None
    revisions: list[Any] | None = None
    payment_id: str | None = None
    note: str | None = Field(None, max_length=4000)


class InvoiceResponse(BaseModel):
    """Vendor invoice response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    work_order_id: str
    vendor_id: str
    invoice_number: str
    date: DateType | None = None
    line_items: list[Any] = Field(default_factory=list)
    subtotal: int = 0
    tax: int = 0
    total: int = 0
    currency: str = "INR"
    status: InvoiceStatus
    document: dict[str, Any] = Field(default_factory=dict)
    files: list[Any] = Field(default_factory=list)
    timeline: list[Any] = Field(default_factory=list)
    revisions: list[Any] = Field(default_factory=list)
    payment_id: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceDetailDataResponse(DataResponse[InvoiceResponse]):
    """Success envelope for a single invoice."""


class InvoiceListDataResponse(ListResponse):
    """Success envelope for paginated invoices."""


class InvoiceTimelineDataResponse(DataResponse[list[Any]]):
    """Success envelope for invoice timeline."""


class VendorSubmitInvoiceRequest(BaseModel):
    """Vendor portal invoice submission."""

    model_config = ConfigDict(extra="forbid")

    invoice_number: str = Field(..., min_length=1, max_length=100)
    vendor_id: str | None = None
    date: DateType | None = None
    line_items: list[Any] = Field(default_factory=list)
    subtotal: int = Field(default=0, ge=0)
    tax: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    currency: str | None = Field(None, max_length=10)
    document: dict[str, Any] = Field(default_factory=dict)
    files: list[Any] = Field(default_factory=list)


class VendorInvoiceListItems(BaseModel):
    """Vendor invoice list wrapper."""

    items: list[InvoiceResponse] = Field(default_factory=list)
    total: int = 0


class VendorInvoiceListDataResponse(DataResponse[VendorInvoiceListItems]):
    """Success envelope for vendor invoice list."""
