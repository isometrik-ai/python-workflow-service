"""API routes for vendor list/search/create (HoA CRM)."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.vendor_service import VendorService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.exceptions.http_exceptions import ValidationException
from app.core.schemas.responses import common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import success_response
from app.schemas.common import ApiKeyScope
from app.schemas.vendors import (
    CreateVendorRequest,
    VendorDetailDataResponse,
    VendorListDataResponse,
    VendorListPayload,
    VendorResponse,
    VendorSearchDataResponse,
    VendorSearchPayload,
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": VendorListDataResponse,
            "description": "Vendors retrieved successfully",
        },
        **common_responses,
    },
    summary="List vendors",
)
async def list_vendors(
    request: Request,
    q: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return vendors merged from HoA CRM and local asset fallback."""
    service = VendorService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    result = await service.list(query=q)
    payload = VendorListPayload(
        total=result["total"],
        data=[VendorResponse.model_validate(item) for item in result["data"]],
    )
    return success_response(
        request=request,
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.get(
    "/search",
    response_model=None,
    responses={
        200: {
            "model": VendorSearchDataResponse,
            "description": "Vendor search completed successfully",
        },
        **common_responses,
    },
    summary="Search vendors",
)
async def search_vendors(
    request: Request,
    q: str = Query(""),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Search vendors via HoA with local fallback."""
    service = VendorService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    result = await service.search(q)
    payload = VendorSearchPayload(
        total=result["total"],
        data=[VendorResponse.model_validate(item) for item in result["data"]],
    )
    return success_response(
        request=request,
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    responses={
        201: {
            "model": VendorDetailDataResponse,
            "description": "Vendor created successfully",
        },
        **common_responses,
    },
    summary="Create vendor",
)
async def create_vendor(
    request: Request,
    body: CreateVendorRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a vendor in HoA CRM (or local fallback)."""
    name = body.name.strip()
    if not name:
        raise ValidationException(message_key="errors.validation_failed")
    service = VendorService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(name)
    payload = VendorResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )
