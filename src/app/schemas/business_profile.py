"""Business profile schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse


class UpdateBusinessProfileRequest(BaseModel):
    """Request body for upserting business profile fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=256)
    legal_name: str | None = Field(None, max_length=256)
    gstin: str | None = Field(None, max_length=32)
    address_line: str | None = Field(None, max_length=4000)
    city: str | None = Field(None, max_length=128)
    state: str | None = Field(None, max_length=128)
    pincode: str | None = Field(None, max_length=16)
    phone: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=256)
    website: str | None = Field(None, max_length=256)
    logo: dict[str, Any] | None = None
    bank_name: str | None = Field(None, max_length=256)
    bank_account: str | None = Field(None, max_length=64)
    bank_ifsc: str | None = Field(None, max_length=32)
    default_wo_notes: str | None = Field(None, max_length=8000)
    default_wo_terms: str | None = Field(None, max_length=8000)


class BusinessProfileResponse(BaseModel):
    """Business profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    name: str = ""
    legal_name: str = ""
    gstin: str = ""
    address_line: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    logo: dict[str, Any] = Field(default_factory=dict)
    bank_name: str = ""
    bank_account: str = ""
    bank_ifsc: str = ""
    default_wo_notes: str = ""
    default_wo_terms: str = ""
    created_at: datetime
    updated_at: datetime


class BusinessProfileDetailDataResponse(DataResponse[BusinessProfileResponse]):
    """Success envelope for business profile."""
