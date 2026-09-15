"""API routes for payments."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.payment_service import PaymentService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse
from app.schemas.common import ApiKeyScope
from app.schemas.payments import (
    CreatePaymentRequest,
    PaymentDetailDataResponse,
    PaymentListDataResponse,
    PaymentResponse,
    UpdatePaymentRequest,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": PaymentListDataResponse,
            "description": "Payments retrieved successfully",
        },
        **common_responses,
    },
    summary="List payments",
)
async def list_payments(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    invoice_id: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated payments for the authenticated tenant/project."""
    service = PaymentService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list(page=page, page_size=page_size, invoice_id=invoice_id)
    payload = [PaymentResponse.model_validate(item).model_dump(mode="json") for item in items]
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
    "/{payment_id}",
    response_model=None,
    responses={
        200: {
            "model": PaymentDetailDataResponse,
            "description": "Payment retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Payment not found"},
        **common_responses,
    },
    summary="Get payment",
)
async def get_payment(
    request: Request,
    payment_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single payment by ID."""
    service = PaymentService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(payment_id)
    payload = PaymentResponse.model_validate(record)
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
            "model": PaymentDetailDataResponse,
            "description": "Payment created successfully",
        },
        **common_responses,
    },
    summary="Create payment",
)
async def create_payment(
    request: Request,
    body: CreatePaymentRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new payment."""
    service = PaymentService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(body.model_dump())
    payload = PaymentResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{payment_id}",
    response_model=None,
    responses={
        200: {
            "model": PaymentDetailDataResponse,
            "description": "Payment updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Payment not found"},
        **common_responses,
    },
    summary="Update payment",
)
async def update_payment(
    request: Request,
    payment_id: str,
    body: UpdatePaymentRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing payment."""
    service = PaymentService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(payment_id, body.model_dump(exclude_unset=True))
    payload = PaymentResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{payment_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Payment deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Payment not found"},
        **common_responses,
    },
    summary="Delete payment",
)
async def delete_payment(
    request: Request,
    payment_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a payment."""
    service = PaymentService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(payment_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
