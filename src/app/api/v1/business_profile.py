"""API routes for business profile singleton."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.business_profile_service import BusinessProfileService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import success_response
from app.schemas.business_profile import (
    BusinessProfileDetailDataResponse,
    BusinessProfileResponse,
    UpdateBusinessProfileRequest,
)
from app.schemas.common import ApiKeyScope

router = APIRouter(prefix="/business-profile", tags=["Business Profile"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": BusinessProfileDetailDataResponse,
            "description": "Business profile retrieved successfully",
        },
        **common_responses,
    },
    summary="Get business profile",
)
async def get_business_profile(
    request: Request,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return the business profile, auto-creating an empty row if missing."""
    service = BusinessProfileService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get()
    payload = BusinessProfileResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.put(
    "",
    response_model=None,
    responses={
        200: {
            "model": BusinessProfileDetailDataResponse,
            "description": "Business profile updated successfully",
        },
        **common_responses,
    },
    summary="Upsert business profile",
)
async def upsert_business_profile(
    request: Request,
    body: UpdateBusinessProfileRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Upsert business profile fields for the authenticated tenant/project."""
    service = BusinessProfileService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.upsert(body.model_dump(exclude_unset=True))
    payload = BusinessProfileResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
