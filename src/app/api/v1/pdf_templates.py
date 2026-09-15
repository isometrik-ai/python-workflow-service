"""API routes for PDF templates."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.pdf_template_service import PdfTemplateService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import DeleteIdResponse
from app.schemas.common import ApiKeyScope
from app.schemas.pdf_templates import (
    CreatePdfTemplateRequest,
    DeleteIdDataResponse,
    PdfTemplateDetailDataResponse,
    PdfTemplateListDataResponse,
    PdfTemplateResponse,
    UpdatePdfTemplateRequest,
)

router = APIRouter(prefix="/pdf-templates", tags=["PDF Templates"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": PdfTemplateListDataResponse,
            "description": "PDF templates retrieved successfully",
        },
        **common_responses,
    },
    summary="List PDF templates",
)
async def list_pdf_templates(
    request: Request,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return all active PDF templates for the authenticated tenant/project."""
    service = PdfTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items = await service.list()
    payload = [PdfTemplateResponse.model_validate(item).model_dump(mode="json") for item in items]
    return list_response(
        request=request,
        items=payload,
        total=len(payload),
        page=1,
        page_size=max(len(payload), 1),
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
    )


@router.get(
    "/{template_id}",
    response_model=None,
    responses={
        200: {
            "model": PdfTemplateDetailDataResponse,
            "description": "PDF template retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "PDF template not found"},
        **common_responses,
    },
    summary="Get PDF template",
)
async def get_pdf_template(
    request: Request,
    template_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single PDF template by ID."""
    service = PdfTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(template_id)
    payload = PdfTemplateResponse.model_validate(record)
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
            "model": PdfTemplateDetailDataResponse,
            "description": "PDF template created successfully",
        },
        **common_responses,
    },
    summary="Create PDF template",
)
async def create_pdf_template(
    request: Request,
    body: CreatePdfTemplateRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new PDF template."""
    service = PdfTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(body.model_dump())
    payload = PdfTemplateResponse.model_validate(record)
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
            "model": PdfTemplateDetailDataResponse,
            "description": "PDF template updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "PDF template not found"},
        **common_responses,
    },
    summary="Update PDF template",
)
async def update_pdf_template(
    request: Request,
    template_id: str,
    body: UpdatePdfTemplateRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing PDF template."""
    service = PdfTemplateService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(template_id, body.model_dump(exclude_unset=True))
    payload = PdfTemplateResponse.model_validate(record)
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
            "description": "PDF template deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "PDF template not found"},
        **common_responses,
    },
    summary="Delete PDF template",
)
async def delete_pdf_template(
    request: Request,
    template_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a PDF template."""
    service = PdfTemplateService(
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
