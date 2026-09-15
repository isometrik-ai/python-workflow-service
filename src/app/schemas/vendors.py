"""Vendor (HoA CRM) schemas."""

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse


class VendorResponse(BaseModel):
    """Vendor summary from HoA or local fallback."""

    id: str
    name: str
    email: str = ""
    phone: str = ""
    industry: str = ""
    status: str = ""
    source: str = "local"


class CreateVendorRequest(BaseModel):
    """Request body for creating a vendor via HoA."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=256)


class VendorListPayload(BaseModel):
    """Vendor list payload (total + data)."""

    total: int
    data: list[VendorResponse]


class VendorListDataResponse(DataResponse[VendorListPayload]):
    """Success envelope for vendor list/search."""


class VendorDetailDataResponse(DataResponse[VendorResponse]):
    """Success envelope for a single vendor."""


class VendorSearchPayload(BaseModel):
    """Vendor search result payload."""

    total: int
    data: list[VendorResponse]


class VendorSearchDataResponse(DataResponse[VendorSearchPayload]):
    """Success envelope for vendor search."""
