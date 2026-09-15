"""API routes for work orders."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.work_order_service import WorkOrderService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response, success_response
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse
from app.schemas.common import ApiKeyScope, TimelineEventRequest
from app.schemas.work_orders import (
    CreateWorkOrderRequest,
    UpdateWorkOrderRequest,
    WorkOrderDetailDataResponse,
    WorkOrderListDataResponse,
    WorkOrderResponse,
    WorkOrderTimelineDataResponse,
)

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": WorkOrderListDataResponse,
            "description": "Work orders retrieved successfully",
        },
        **common_responses,
    },
    summary="List work orders",
)
async def list_work_orders(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    state: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated work orders for the authenticated tenant/project."""
    service = WorkOrderService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list(page=page, page_size=page_size, state=state)
    payload = [WorkOrderResponse.model_validate(item).model_dump(mode="json") for item in items]
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
    "/{work_order_id}",
    response_model=None,
    responses={
        200: {
            "model": WorkOrderDetailDataResponse,
            "description": "Work order retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Work order not found"},
        **common_responses,
    },
    summary="Get work order",
)
async def get_work_order(
    request: Request,
    work_order_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single work order by ID."""
    service = WorkOrderService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(work_order_id)
    payload = WorkOrderResponse.model_validate(record)
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
            "model": WorkOrderDetailDataResponse,
            "description": "Work order created successfully",
        },
        **common_responses,
    },
    summary="Create work order",
)
async def create_work_order(
    request: Request,
    body: CreateWorkOrderRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new work order."""
    service = WorkOrderService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(body.model_dump())
    payload = WorkOrderResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{work_order_id}",
    response_model=None,
    responses={
        200: {
            "model": WorkOrderDetailDataResponse,
            "description": "Work order updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Work order not found"},
        **common_responses,
    },
    summary="Update work order",
)
async def update_work_order(
    request: Request,
    work_order_id: str,
    body: UpdateWorkOrderRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing work order."""
    service = WorkOrderService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(work_order_id, body.model_dump(exclude_unset=True))
    payload = WorkOrderResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{work_order_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Work order deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Work order not found"},
        **common_responses,
    },
    summary="Delete work order",
)
async def delete_work_order(
    request: Request,
    work_order_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a work order."""
    service = WorkOrderService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(work_order_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.post(
    "/{work_order_id}/timeline",
    response_model=None,
    responses={
        200: {
            "model": WorkOrderTimelineDataResponse,
            "description": "Work order timeline updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Work order not found"},
        **common_responses,
    },
    summary="Append work order timeline event",
)
async def append_work_order_timeline(
    request: Request,
    work_order_id: str,
    body: TimelineEventRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Append an event to a work order timeline."""
    service = WorkOrderService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    timeline = await service.append_timeline(
        work_order_id,
        event_type=body.type,
        note=body.note,
        by=body.by,
        from_=body.from_,
        to=body.to,
    )
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=timeline,
    )
