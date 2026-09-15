"""API routes for assets."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.asset_service import AssetService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import ConflictErrorDoc, NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import (
    AssetDetailDataResponse,
    AssetListDataResponse,
    AssetResponse,
    CreateAssetRequest,
    DeleteIdDataResponse,
    DeleteIdResponse,
    UpdateAssetRequest,
)
from app.schemas.common import ApiKeyScope

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": AssetListDataResponse,
            "description": "Assets retrieved successfully",
        },
        **common_responses,
    },
    summary="List assets",
)
async def list_assets(
    request: Request,
    *,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    category_id: str | None = Query(None),
    status: str | None = Query(None),
    location_id: str | None = Query(None),
    contract_id: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated assets for the authenticated tenant/project."""
    service = AssetService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list(
        page=page,
        page_size=page_size,
        search=search,
        category_id=category_id,
        status=status,
        location_id=location_id,
        contract_id=contract_id,
    )
    payload = [AssetResponse.model_validate(item).model_dump(mode="json") for item in items]
    return list_response(
        request=request,
        items=payload,
        total=total,
        page=page,
        page_size=page_size,
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
    )


@router.get(
    "/{asset_id}",
    response_model=None,
    responses={
        200: {
            "model": AssetDetailDataResponse,
            "description": "Asset retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Asset not found"},
        **common_responses,
    },
    summary="Get asset",
)
async def get_asset(
    request: Request,
    asset_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single asset by ID."""
    service = AssetService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(asset_id)
    payload = AssetResponse.model_validate(record)
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
            "model": AssetDetailDataResponse,
            "description": "Asset created successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Asset category not found"},
        409: {
            "model": ConflictErrorDoc,
            "description": "Asset code already exists for project",
        },
        **common_responses,
    },
    summary="Create asset",
)
async def create_asset(
    request: Request,
    body: CreateAssetRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new asset."""
    service = AssetService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(body.model_dump(exclude_unset=True))
    payload = AssetResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{asset_id}",
    response_model=None,
    responses={
        200: {
            "model": AssetDetailDataResponse,
            "description": "Asset updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Asset or category not found"},
        409: {
            "model": ConflictErrorDoc,
            "description": "Asset code already exists for project",
        },
        **common_responses,
    },
    summary="Update asset",
)
async def update_asset(
    request: Request,
    asset_id: str,
    body: UpdateAssetRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing asset."""
    service = AssetService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(asset_id, body.model_dump(exclude_unset=True))
    payload = AssetResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{asset_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Asset deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Asset not found"},
        **common_responses,
    },
    summary="Delete asset",
)
async def delete_asset(
    request: Request,
    asset_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete an asset."""
    service = AssetService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(asset_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
