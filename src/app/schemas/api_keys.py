"""API key request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas.responses.base import DataResponse


class CreateApiKeyRequest(BaseModel):
    """Request body for creating a project API key."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(..., min_length=1, max_length=128)
    project_id: str = Field(..., min_length=1, max_length=128)
    name: str = Field(default="API Key", min_length=1, max_length=255)


class ApiKeyResponse(BaseModel):
    """Public API key metadata for a tenant/project."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    project_id: str
    name: str
    key_prefix: str
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Create response includes the raw key once."""

    key: str


class ApiKeyDetailDataResponse(DataResponse[ApiKeyResponse]):
    """Success envelope for GET /api/v1/api-keys."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Resource retrieved successfully",
                "status_code": 200,
                "code": "2000",
                "data": {
                    "id": "api_key_a1b2c3d4e5f6",
                    "tenant_id": "tenant123",
                    "project_id": "project123",
                    "name": "Integration Key",
                    "key_prefix": "abc123def456",
                    "last_used_at": None,
                    "created_at": "2026-09-12T10:30:00+00:00",
                    "updated_at": "2026-09-12T10:30:00+00:00",
                },
            },
        },
    )


class ApiKeyCreatedDataResponse(DataResponse[ApiKeyCreatedResponse]):
    """Success envelope for POST /api/v1/api-keys."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "message": "Resource created successfully",
                "status_code": 201,
                "code": "2001",
                "data": {
                    "id": "api_key_a1b2c3d4e5f6",
                    "tenant_id": "tenant123",
                    "project_id": "project123",
                    "name": "Integration Key",
                    "key_prefix": "abc123def456",
                    "key": "wo_abc123...shown-once",
                    "last_used_at": None,
                    "created_at": "2026-09-12T10:30:00+00:00",
                    "updated_at": "2026-09-12T10:30:00+00:00",
                },
            },
        },
    )
