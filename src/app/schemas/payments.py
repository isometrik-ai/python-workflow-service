"""Payment domain schemas and enums."""

from datetime import date as DateType
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse


class PaymentMethod(str, Enum):
    """Method used to settle a vendor payment."""

    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    CASH = "cash"
    UPI = "upi"
    OTHER = "other"


class PaymentStatus(str, Enum):
    """Processing status of a vendor payment."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    VOIDED = "voided"


class CreatePaymentRequest(BaseModel):
    """Request body for creating a payment."""

    model_config = ConfigDict(extra="forbid")

    amount: int = Field(..., ge=0)
    invoice_id: str | None = None
    work_order_id: str | None = None
    currency: str | None = Field(None, max_length=10)
    method: PaymentMethod | None = None
    reference: str | None = Field(None, max_length=255)
    date: DateType | None = None
    status: PaymentStatus | None = None
    receipt: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(None, max_length=2000)


class UpdatePaymentRequest(BaseModel):
    """Request body for updating a payment."""

    model_config = ConfigDict(extra="forbid")

    amount: int | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=10)
    method: PaymentMethod | None = None
    reference: str | None = Field(None, max_length=255)
    date: DateType | None = None
    status: PaymentStatus | None = None
    receipt: dict[str, Any] | None = None
    notes: str | None = Field(None, max_length=2000)


class PaymentResponse(BaseModel):
    """Payment response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    invoice_id: str | None = None
    work_order_id: str | None = None
    amount: int
    currency: str = "INR"
    method: PaymentMethod
    reference: str | None = None
    date: DateType | None = None
    status: PaymentStatus
    receipt: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PaymentDetailDataResponse(DataResponse[PaymentResponse]):
    """Success envelope for a single payment."""


class PaymentListDataResponse(ListResponse):
    """Success envelope for paginated payments."""
