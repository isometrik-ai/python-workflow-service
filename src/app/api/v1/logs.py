"""API routes for audit and webhook delivery logs."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.log_service import LogService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import list_response
from app.schemas.common import ApiKeyScope
from app.schemas.logs import (
    ApiCallLogListDataResponse,
    ApiCallLogResponse,
    AuditEventListDataResponse,
    AuditEventResponse,
    WebhookDeliveryListDataResponse,
    WebhookDeliveryResponse,
)

router = APIRouter(tags=["Logs"])


@router.get(
    "/audit-events",
    response_model=None,
    responses={
        200: {
            "model": AuditEventListDataResponse,
            "description": "Audit events retrieved successfully",
        },
        **common_responses,
    },
    summary="List audit events",
)
async def list_audit_events(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    entity: str | None = Query(None),
    entity_id: str | None = Query(None),
    source: str | None = Query(None),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated audit events for the authenticated tenant/project."""
    service = LogService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list_audit_events(
        page=page,
        page_size=page_size,
        entity=entity,
        entity_id=entity_id,
        source=source,
    )
    payload = [AuditEventResponse.model_validate(item).model_dump(mode="json") for item in items]
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
    "/webhook-deliveries",
    response_model=None,
    responses={
        200: {
            "model": WebhookDeliveryListDataResponse,
            "description": "Webhook deliveries retrieved successfully",
        },
        **common_responses,
    },
    summary="List webhook deliveries",
)
async def list_webhook_deliveries(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated webhook delivery logs for the authenticated tenant/project."""
    service = LogService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list_webhook_deliveries(page=page, page_size=page_size)
    payload = [
        WebhookDeliveryResponse.model_validate(item).model_dump(mode="json") for item in items
    ]
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
    "/api-call-logs",
    response_model=None,
    responses={
        200: {
            "model": ApiCallLogListDataResponse,
            "description": "API call logs retrieved successfully",
        },
        **common_responses,
    },
    summary="List API call logs",
)
async def list_api_call_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=500),
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return paginated API call logs for the authenticated tenant/project."""
    service = LogService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items, total = await service.list_api_call_logs(
        page=page,
        page_size=page_size,
        limit=limit,
    )
    payload = [ApiCallLogResponse.model_validate(item).model_dump(mode="json") for item in items]
    return list_response(
        request=request,
        items=payload,
        total=total,
        page=page,
        page_size=page_size,
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
    )
