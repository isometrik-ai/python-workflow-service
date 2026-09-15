"""API routes for form templates."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.form_template_service import FormTemplateService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse
from app.schemas.common import ApiKeyScope
from app.schemas.form_templates import (
    CreateFormTemplateRequest,
    FormTemplateDetailDataResponse,
    FormTemplateListDataResponse,
    FormTemplateResponse,
    UpdateFormTemplateRequest,
)

router = APIRouter(prefix="/form-templates", tags=["Form Templates"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": FormTemplateListDataResponse,
            "description": "Form templates retrieved successfully",
        },
        **common_responses,
    },
    summary="List form templates",
)
async def list_form_templates(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated form templates for the authenticated tenant/project."""
    service = FormTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list(page=page, page_size=page_size, search=search)
    payload = [FormTemplateResponse.model_validate(item).model_dump(mode="json") for item in items]
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
    "/{template_id}",
    response_model=None,
    responses={
        200: {
            "model": FormTemplateDetailDataResponse,
            "description": "Form template retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Form template not found"},
        **common_responses,
    },
    summary="Get form template",
)
async def get_form_template(
    request: Request,
    template_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single form template by ID."""
    service = FormTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(template_id)
    payload = FormTemplateResponse.model_validate(record)
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
            "model": FormTemplateDetailDataResponse,
            "description": "Form template created successfully",
        },
        **common_responses,
    },
    summary="Create form template",
)
async def create_form_template(
    request: Request,
    body: CreateFormTemplateRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new form template."""
    service = FormTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(
        name=body.name,
        description=body.description,
        schema=body.schema,
    )
    payload = FormTemplateResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{template_id}",
    response_model=None,
    responses={
        200: {
            "model": FormTemplateDetailDataResponse,
            "description": "Form template updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Form template not found"},
        **common_responses,
    },
    summary="Update form template",
)
async def update_form_template(
    request: Request,
    template_id: str,
    body: UpdateFormTemplateRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing form template."""
    service = FormTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(
        template_id,
        name=body.name,
        description=body.description,
        schema=body.schema,
    )
    payload = FormTemplateResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{template_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Form template deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Form template not found"},
        **common_responses,
    },
    summary="Delete form template",
)
async def delete_form_template(
    request: Request,
    template_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a form template."""
    service = FormTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(template_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
