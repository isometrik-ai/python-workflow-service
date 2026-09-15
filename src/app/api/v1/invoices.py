"""API routes for vendor invoices."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.invoice_service import InvoiceService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse
from app.schemas.common import ApiKeyScope, TimelineEventRequest
from app.schemas.invoices import (
    CreateInvoiceRequest,
    InvoiceDetailDataResponse,
    InvoiceListDataResponse,
    InvoiceResponse,
    InvoiceTimelineDataResponse,
    UpdateInvoiceRequest,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": InvoiceListDataResponse,
            "description": "Invoices retrieved successfully",
        },
        **common_responses,
    },
    summary="List vendor invoices",
)
async def list_invoices(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    work_order_id: str | None = Query(None),
    status: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated vendor invoices for the authenticated tenant/project."""
    service = InvoiceService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list(
        page=page,
        page_size=page_size,
        work_order_id=work_order_id,
        status=status,
    )
    payload = [InvoiceResponse.model_validate(item).model_dump(mode="json") for item in items]
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
    "/{invoice_id}",
    response_model=None,
    responses={
        200: {
            "model": InvoiceDetailDataResponse,
            "description": "Invoice retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Invoice not found"},
        **common_responses,
    },
    summary="Get vendor invoice",
)
async def get_invoice(
    request: Request,
    invoice_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single vendor invoice by ID."""
    service = InvoiceService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(invoice_id)
    payload = InvoiceResponse.model_validate(record)
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
            "model": InvoiceDetailDataResponse,
            "description": "Invoice created successfully",
        },
        **common_responses,
    },
    summary="Create vendor invoice",
)
async def create_invoice(
    request: Request,
    body: CreateInvoiceRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new vendor invoice."""
    service = InvoiceService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(body.model_dump(mode="json"))
    payload = InvoiceResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{invoice_id}",
    response_model=None,
    responses={
        200: {
            "model": InvoiceDetailDataResponse,
            "description": "Invoice updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Invoice not found"},
        **common_responses,
    },
    summary="Update vendor invoice",
)
async def update_invoice(
    request: Request,
    invoice_id: str,
    body: UpdateInvoiceRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing vendor invoice."""
    service = InvoiceService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(invoice_id, body.model_dump(exclude_unset=True, mode="json"))
    payload = InvoiceResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{invoice_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Invoice deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Invoice not found"},
        **common_responses,
    },
    summary="Delete vendor invoice",
)
async def delete_invoice(
    request: Request,
    invoice_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a vendor invoice."""
    service = InvoiceService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(invoice_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.post(
    "/{invoice_id}/timeline",
    response_model=None,
    responses={
        200: {
            "model": InvoiceTimelineDataResponse,
            "description": "Invoice timeline updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Invoice not found"},
        **common_responses,
    },
    summary="Append invoice timeline event",
)
async def append_invoice_timeline(
    request: Request,
    invoice_id: str,
    body: TimelineEventRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Append an event to a vendor invoice timeline."""
    service = InvoiceService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    timeline = await service.append_timeline(
        invoice_id,
        event_type=body.type,
        note=body.note,
        by=body.by,
    )
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=timeline,
    )
