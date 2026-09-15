"""API routes for asset categories."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.asset_category_service import AssetCategoryService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import (
    AssetCategoryDetailDataResponse,
    AssetCategoryListDataResponse,
    AssetCategoryResponse,
    CreateAssetCategoryRequest,
    DeleteIdDataResponse,
    DeleteIdResponse,
    UpdateAssetCategoryRequest,
)
from app.schemas.common import ApiKeyScope

router = APIRouter(prefix="/asset-categories", tags=["Asset Categories"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": AssetCategoryListDataResponse,
            "description": "Asset categories retrieved successfully",
        },
        **common_responses,
    },
    summary="List asset categories",
)
async def list_asset_categories(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated asset categories for the authenticated tenant/project."""
    service = AssetCategoryService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list(page=page, page_size=page_size, search=search)
    payload = [AssetCategoryResponse.model_validate(item).model_dump(mode="json") for item in items]
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
    "/{category_id}",
    response_model=None,
    responses={
        200: {
            "model": AssetCategoryDetailDataResponse,
            "description": "Asset category retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Asset category not found"},
        **common_responses,
    },
    summary="Get asset category",
)
async def get_asset_category(
    request: Request,
    category_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single asset category by ID."""
    service = AssetCategoryService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(category_id)
    payload = AssetCategoryResponse.model_validate(record)
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
            "model": AssetCategoryDetailDataResponse,
            "description": "Asset category created successfully",
        },
        **common_responses,
    },
    summary="Create asset category",
)
async def create_asset_category(
    request: Request,
    body: CreateAssetCategoryRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new asset category."""
    service = AssetCategoryService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(
        name=body.name,
        description=body.description,
        parent_id=body.parent_id,
    )
    payload = AssetCategoryResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{category_id}",
    response_model=None,
    responses={
        200: {
            "model": AssetCategoryDetailDataResponse,
            "description": "Asset category updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Asset category not found"},
        **common_responses,
    },
    summary="Update asset category",
)
async def update_asset_category(
    request: Request,
    category_id: str,
    body: UpdateAssetCategoryRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing asset category."""
    service = AssetCategoryService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(
        category_id,
        name=body.name,
        description=body.description,
        parent_id=body.parent_id,
    )
    payload = AssetCategoryResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{category_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Asset category deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Asset category not found"},
        **common_responses,
    },
    summary="Delete asset category",
)
async def delete_asset_category(
    request: Request,
    category_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete an asset category."""
    service = AssetCategoryService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(category_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
