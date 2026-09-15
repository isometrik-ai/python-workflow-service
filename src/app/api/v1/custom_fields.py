"""API routes for custom field definitions."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.custom_field_service import CustomFieldService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.common import ApiKeyScope
from app.schemas.custom_fields import (
    CreateCustomFieldRequest,
    CustomFieldDetailDataResponse,
    CustomFieldListDataResponse,
    CustomFieldResponse,
    DeleteCustomFieldDataResponse,
    DeleteCustomFieldResponse,
    UpdateCustomFieldRequest,
)

router = APIRouter(prefix="/custom-fields", tags=["Custom Fields"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": CustomFieldListDataResponse,
            "description": "Custom fields retrieved successfully",
        },
        **common_responses,
    },
    summary="List custom fields",
)
async def list_custom_fields(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    scope: str | None = Query(None),
    category_id: str | None = Query(None),
    api_scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated custom fields for the authenticated tenant/project."""
    service = CustomFieldService(
        db=db,
        tenant_id=api_scope.tenant_id,
        project_id=api_scope.project_id,
    )
    items, total = await service.list(
        page=page,
        page_size=page_size,
        search=search,
        scope=scope,
        category_id=category_id,
    )
    payload = [CustomFieldResponse.model_validate(item).model_dump(mode="json") for item in items]
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
    "/{field_id}",
    response_model=None,
    responses={
        200: {
            "model": CustomFieldDetailDataResponse,
            "description": "Custom field retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Custom field not found"},
        **common_responses,
    },
    summary="Get custom field",
)
async def get_custom_field(
    request: Request,
    field_id: str,
    api_scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single custom field by ID."""
    service = CustomFieldService(
        db=db,
        tenant_id=api_scope.tenant_id,
        project_id=api_scope.project_id,
    )
    record = await service.get(field_id)
    payload = CustomFieldResponse.model_validate(record)
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
            "model": CustomFieldDetailDataResponse,
            "description": "Custom field created successfully",
        },
        **common_responses,
    },
    summary="Create custom field",
)
async def create_custom_field(
    request: Request,
    body: CreateCustomFieldRequest,
    api_scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new custom field definition."""
    service = CustomFieldService(
        db=db,
        tenant_id=api_scope.tenant_id,
        project_id=api_scope.project_id,
    )
    record = await service.create(body.model_dump())
    payload = CustomFieldResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{field_id}",
    response_model=None,
    responses={
        200: {
            "model": CustomFieldDetailDataResponse,
            "description": "Custom field updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Custom field not found"},
        **common_responses,
    },
    summary="Update custom field",
)
async def update_custom_field(
    request: Request,
    field_id: str,
    body: UpdateCustomFieldRequest,
    api_scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing custom field definition."""
    service = CustomFieldService(
        db=db,
        tenant_id=api_scope.tenant_id,
        project_id=api_scope.project_id,
    )
    record = await service.update(field_id, body.model_dump(exclude_unset=True))
    payload = CustomFieldResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{field_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteCustomFieldDataResponse,
            "description": "Custom field deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Custom field not found"},
        **common_responses,
    },
    summary="Delete custom field",
)
async def delete_custom_field(
    request: Request,
    field_id: str,
    api_scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a custom field definition."""
    service = CustomFieldService(
        db=db,
        tenant_id=api_scope.tenant_id,
        project_id=api_scope.project_id,
    )
    deleted_id = await service.delete(field_id)
    payload = DeleteCustomFieldResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
