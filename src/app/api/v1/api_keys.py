"""API routes for project API keys."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.api_key_service import ApiKeyService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import (
    ConflictErrorDoc,
    NotFoundErrorDoc,
    UnauthorizedErrorDoc,
    common_responses,
)
from app.core.security.api_key_auth import get_api_key_scope
from app.core.security.internal_auth import require_internal_token
from app.core.utils.response_factory import success_response
from app.schemas.api_keys import (
    ApiKeyCreatedDataResponse,
    ApiKeyCreatedResponse,
    ApiKeyDetailDataResponse,
    ApiKeyResponse,
    CreateApiKeyRequest,
)
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse
from app.schemas.common import ApiKeyScope

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": ApiKeyDetailDataResponse,
            "description": "Active API key retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "No active API key for tenant/project"},
        **common_responses,
    },
    summary="Get project API key",
)
async def get_project_api_key(
    request: Request,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return the active API key for the authenticated tenant/project (one per scope)."""
    service = ApiKeyService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get_project_api_key()
    payload = ApiKeyResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    responses={
        201: {
            "model": ApiKeyCreatedDataResponse,
            "description": "API key created successfully",
        },
        401: {
            "model": UnauthorizedErrorDoc,
            "description": "Missing or invalid X-Internal-Token",
        },
        409: {
            "model": ConflictErrorDoc,
            "description": "An API key already exists for tenant/project",
        },
        **common_responses,
    },
    summary="Create project API key",
)
async def create_api_key(
    request: Request,
    body: CreateApiKeyRequest,
    _: None = Depends(require_internal_token),
    db: AsyncSession = Depends(async_get_db),
):
    """Bootstrap a project API key (requires X-Internal-Token, not an existing API key)."""
    service = ApiKeyService(db=db)
    record = await service.create_api_key(
        tenant_id=body.tenant_id,
        project_id=body.project_id,
        name=body.name,
    )
    payload = ApiKeyCreatedResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.delete(
    "/{key_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "API key revoked successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "API key not found"},
        **common_responses,
    },
    summary="Revoke project API key",
)
async def revoke_api_key(
    request: Request,
    key_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Revoke the active API key for the authenticated tenant/project."""
    service = ApiKeyService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.revoke_api_key(key_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
