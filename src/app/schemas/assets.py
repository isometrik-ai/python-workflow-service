"""Asset and asset category schemas."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse, ListResponse


class AssetStatus(str, Enum):
    """Operational status of a physical asset."""

    OPERATIONAL = "operational"
    UNDER_REPAIR = "under_repair"
    FAULTY = "faulty"
    DECOMMISSIONED = "decommissioned"


class CreateAssetCategoryRequest(BaseModel):
    """Request body for creating an asset category."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    parent_id: str | None = None


class UpdateAssetCategoryRequest(BaseModel):
    """Request body for updating an asset category."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    parent_id: str | None = None


class AssetCategoryResponse(BaseModel):
    """Asset category response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    name: str
    description: str = ""
    parent_id: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssetCategoryDetailDataResponse(DataResponse[AssetCategoryResponse]):
    """Success envelope for a single asset category."""


class AssetCategoryListDataResponse(ListResponse):
    """Success envelope for paginated asset categories."""


class CreateAssetRequest(BaseModel):
    """Request body for creating an asset."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    category_id: str
    make: str | None = Field(None, max_length=255)
    model: str | None = Field(None, max_length=255)
    serial_number: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=4000)
    status: AssetStatus | None = None
    location_id: str | None = None
    location_text: str | None = Field(None, max_length=500)
    landmark_note: str | None = Field(None, max_length=500)
    photos: list[str] = Field(default_factory=list)
    associated_parts: list[Any] = Field(default_factory=list)
    purchase_date: date | None = None
    purchase_cost: int | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=10)
    supplier: str | None = Field(None, max_length=255)
    supplier_vendor_id: str | None = None
    purchase_order_number: str | None = Field(None, max_length=100)
    invoice_ref: str | None = Field(None, max_length=100)
    install_date: date | None = None
    warranty_start: date | None = None
    warranty_expiry: date | None = None
    warranty_terms: str | None = Field(None, max_length=2000)
    documents: list[str] = Field(default_factory=list)
    custom_field_values: dict[str, Any] = Field(default_factory=dict)
    contract_id: str | None = None


class UpdateAssetRequest(BaseModel):
    """Request body for updating an asset."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=100)
    category_id: str | None = None
    make: str | None = Field(None, max_length=255)
    model: str | None = Field(None, max_length=255)
    serial_number: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=4000)
    status: AssetStatus | None = None
    location_id: str | None = None
    location_text: str | None = Field(None, max_length=500)
    landmark_note: str | None = Field(None, max_length=500)
    photos: list[str] | None = None
    associated_parts: list[Any] | None = None
    purchase_date: date | None = None
    purchase_cost: int | None = Field(None, ge=0)
    currency: str | None = Field(None, max_length=10)
    supplier: str | None = Field(None, max_length=255)
    supplier_vendor_id: str | None = None
    purchase_order_number: str | None = Field(None, max_length=100)
    invoice_ref: str | None = Field(None, max_length=100)
    install_date: date | None = None
    warranty_start: date | None = None
    warranty_expiry: date | None = None
    warranty_terms: str | None = Field(None, max_length=2000)
    documents: list[str] | None = None
    custom_field_values: dict[str, Any] | None = None
    contract_id: str | None = None


class AssetResponse(BaseModel):
    """Asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    name: str
    code: str
    make: str | None = None
    model: str | None = None
    serial_number: str | None = None
    description: str | None = None
    category_id: str
    status: AssetStatus
    location_id: str | None = None
    location_text: str | None = None
    landmark_note: str | None = None
    photos: list[str] = Field(default_factory=list)
    associated_parts: list[Any] = Field(default_factory=list)
    purchase_date: date | None = None
    purchase_cost: int | None = None
    currency: str = "INR"
    supplier: str | None = None
    supplier_vendor_id: str | None = None
    purchase_order_number: str | None = None
    invoice_ref: str | None = None
    install_date: date | None = None
    warranty_start: date | None = None
    warranty_expiry: date | None = None
    warranty_terms: str | None = None
    documents: list[str] = Field(default_factory=list)
    custom_field_values: dict[str, Any] = Field(default_factory=dict)
    contract_id: str | None = None
    record_status: str = "active"
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssetDetailDataResponse(DataResponse[AssetResponse]):
    """Success envelope for a single asset."""


class AssetListDataResponse(ListResponse):
    """Success envelope for paginated assets."""


class DeleteIdResponse(BaseModel):
    """Delete confirmation payload."""

    id: str


class DeleteIdDataResponse(DataResponse[DeleteIdResponse]):
    """Success envelope for delete operations."""
