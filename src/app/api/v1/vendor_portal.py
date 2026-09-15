"""Vendor portal routes scoped by vendor token."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.vendor_portal_service import VendorPortalService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import common_responses
from app.core.security.vendor_auth import get_work_order_from_vendor_token
from app.core.utils.response_factory import success_response
from app.schemas.invoices import (
    InvoiceDetailDataResponse,
    InvoiceResponse,
    VendorInvoiceListDataResponse,
    VendorInvoiceListItems,
    VendorSubmitInvoiceRequest,
)
from app.schemas.work_orders import (
    VendorUpdateWorkOrderRequest,
    WorkOrderDetailDataResponse,
    WorkOrderResponse,
)

router = APIRouter(prefix="/vendor", tags=["Vendor Portal"])


@router.get(
    "/work-order",
    response_model=None,
    responses={
        200: {
            "model": WorkOrderDetailDataResponse,
            "description": "Vendor work order retrieved successfully",
        },
        **common_responses,
    },
    summary="Get vendor work order",
)
async def vendor_get_work_order(
    request: Request,
    work_order: dict = Depends(get_work_order_from_vendor_token),
):
    """Return the work order scoped to the vendor portal token."""
    payload = WorkOrderResponse.model_validate(work_order)
    return success_response(
        request=request,
        message_key="success.retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.patch(
    "/work-order",
    response_model=None,
    responses={
        200: {
            "model": WorkOrderDetailDataResponse,
            "description": "Vendor work order updated successfully",
        },
        **common_responses,
    },
    summary="Update vendor work order",
)
async def vendor_update_work_order(
    request: Request,
    body: VendorUpdateWorkOrderRequest,
    work_order: dict = Depends(get_work_order_from_vendor_token),
    db: AsyncSession = Depends(async_get_db),
):
    """Update a vendor-scoped work order."""
    service = VendorPortalService(db=db)
    record = await service.update_work_order(
        work_order,
        body.model_dump(exclude_unset=True),
    )
    payload = WorkOrderResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.post(
    "/invoices",
    status_code=status.HTTP_201_CREATED,
    response_model=None,
    responses={
        201: {
            "model": InvoiceDetailDataResponse,
            "description": "Vendor invoice submitted successfully",
        },
        **common_responses,
    },
    summary="Submit vendor invoice",
)
async def vendor_submit_invoice(
    request: Request,
    body: VendorSubmitInvoiceRequest,
    work_order: dict = Depends(get_work_order_from_vendor_token),
    db: AsyncSession = Depends(async_get_db),
):
    """Submit an invoice for the vendor-scoped work order."""
    service = VendorPortalService(db=db)
    record = await service.submit_invoice(
        work_order,
        body.model_dump(),
    )
    payload = InvoiceResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.get(
    "/invoices",
    response_model=None,
    responses={
        200: {
            "model": VendorInvoiceListDataResponse,
            "description": "Vendor invoices retrieved successfully",
        },
        **common_responses,
    },
    summary="List vendor invoices",
)
async def vendor_list_invoices(
    request: Request,
    work_order: dict = Depends(get_work_order_from_vendor_token),
    db: AsyncSession = Depends(async_get_db),
):
    """List invoices for the vendor-scoped work order."""
    service = VendorPortalService(db=db)
    items, total = await service.list_invoices(work_order)
    payload = VendorInvoiceListItems(
        items=[InvoiceResponse.model_validate(item) for item in items],
        total=total,
    ).model_dump(mode="json")
    return success_response(
        request=request,
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload,
    )
