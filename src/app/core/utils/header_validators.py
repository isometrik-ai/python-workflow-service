"""Header validation dependencies for work-order routes."""

from typing import Annotated

from fastapi import Header
from pydantic import BaseModel, ConfigDict, Field

from app.core.constants.status_codes import CustomStatusCode
from app.core.exceptions.http_exceptions import ValidationException


class HeaderBase(BaseModel):
    """Base tenancy headers shared across staff routes."""

    x_tenant_id: str = Field(..., description="Tenant ID", alias="x-tenant-id")
    x_project_id: str = Field(..., description="Project ID", alias="x-project-id")
    x_request_id: str | None = Field(
        default=None,
        description="Request ID for attribution",
        alias="x-request-id",
    )

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class HeaderTenancy(HeaderBase):
    """Tenancy headers required on staff routes."""


class HeaderApiKeyAuth(BaseModel):
    """API key and optional tenancy headers."""

    x_api_key: str = Field(default="", description="API key", alias="x-api-key")
    x_tenant_id: str = Field(default="", description="Tenant ID", alias="x-tenant-id")
    x_project_id: str = Field(default="", description="Project ID", alias="x-project-id")
    x_request_id: str | None = Field(
        default=None,
        description="Request ID for attribution",
        alias="x-request-id",
    )

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class HeaderInternalAuth(BaseModel):
    """Internal service token header."""

    x_internal_token: str | None = Field(
        default=None,
        description="Internal service token",
        alias="x-internal-token",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class HeaderSchedulerAuth(BaseModel):
    """Scheduler auth accepts internal token or API key headers."""

    x_internal_token: str | None = Field(
        default=None,
        description="Internal service token",
        alias="x-internal-token",
    )
    x_api_key: str = Field(default="", description="API key", alias="x-api-key")
    x_tenant_id: str = Field(default="", description="Tenant ID", alias="x-tenant-id")
    x_project_id: str = Field(default="", description="Project ID", alias="x-project-id")
    x_request_id: str | None = Field(
        default=None,
        description="Request ID for attribution",
        alias="x-request-id",
    )

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class HeaderVendorAuth(BaseModel):
    """Vendor portal token header."""

    x_vendor_token: str = Field(..., description="Vendor access token", alias="x-vendor-token")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )


async def get_tenancy_header(
    x_tenant_id: Annotated[str, Header(alias="x-tenant-id")],
    x_project_id: Annotated[str, Header(alias="x-project-id")],
    x_request_id: Annotated[str | None, Header(alias="x-request-id")] = None,
) -> HeaderTenancy:
    """Get and validate tenancy headers."""
    return HeaderTenancy(
        **{
            "x-tenant-id": x_tenant_id,
            "x-project-id": x_project_id,
            "x-request-id": x_request_id,
        }
    )


async def get_header_api_key_auth(
    x_api_key: Annotated[str, Header(alias="x-api-key")] = "",
    x_tenant_id: Annotated[str, Header(alias="x-tenant-id")] = "",
    x_project_id: Annotated[str, Header(alias="x-project-id")] = "",
    x_request_id: Annotated[str | None, Header(alias="x-request-id")] = None,
) -> HeaderApiKeyAuth:
    """Get API key auth headers."""
    return HeaderApiKeyAuth(
        **{
            "x-api-key": x_api_key,
            "x-tenant-id": x_tenant_id,
            "x-project-id": x_project_id,
            "x-request-id": x_request_id,
        }
    )


async def get_header_internal_auth(
    x_internal_token: Annotated[str | None, Header(alias="x-internal-token")] = None,
) -> HeaderInternalAuth:
    """Get internal service token header."""
    return HeaderInternalAuth(**{"x-internal-token": x_internal_token})


async def get_header_scheduler_auth(
    x_internal_token: Annotated[str | None, Header(alias="x-internal-token")] = None,
    x_api_key: Annotated[str, Header(alias="x-api-key")] = "",
    x_tenant_id: Annotated[str, Header(alias="x-tenant-id")] = "",
    x_project_id: Annotated[str, Header(alias="x-project-id")] = "",
    x_request_id: Annotated[str | None, Header(alias="x-request-id")] = None,
) -> HeaderSchedulerAuth:
    """Get scheduler auth headers."""
    return HeaderSchedulerAuth(
        **{
            "x-internal-token": x_internal_token,
            "x-api-key": x_api_key,
            "x-tenant-id": x_tenant_id,
            "x-project-id": x_project_id,
            "x-request-id": x_request_id,
        }
    )


async def get_header_vendor_auth(
    x_vendor_token: Annotated[str, Header(alias="x-vendor-token")],
) -> HeaderVendorAuth:
    """Get vendor portal token header."""
    token = (x_vendor_token or "").strip()
    if not token:
        raise ValidationException(
            message_key="auth.errors.unauthorized",
            custom_code=CustomStatusCode.UNAUTHORIZED,
        )
    return HeaderVendorAuth(**{"x-vendor-token": token})


# Backward-compatible alias.
get_header_tenancy = get_tenancy_header
