"""API routes for webhook trigger configuration."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.trigger_service import TriggerService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import NotFoundErrorDoc, common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import success_response
from app.schemas.assets import DeleteIdDataResponse, DeleteIdResponse
from app.schemas.common import ApiKeyScope
from app.schemas.triggers import (
    CreateTriggerRequest,
    TriggerDetailDataResponse,
    TriggerListDataResponse,
    TriggerListItems,
    TriggerResponse,
    TriggerTestDataResponse,
    TriggerTestResult,
    UpdateTriggerRequest,
)

router = APIRouter(prefix="/triggers", tags=["Triggers"])


@router.get(
    "",
    response_model=None,
    responses={
        200: {
            "model": TriggerListDataResponse,
            "description": "Triggers retrieved successfully",
        },
        **common_responses,
    },
    summary="List webhook triggers",
)
async def list_triggers(
    request: Request,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return webhook trigger configurations for the authenticated tenant/project."""
    service = TriggerService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    items = await service.list()
    payload = TriggerListItems(
        items=[TriggerResponse.model_validate(item) for item in items]
    ).model_dump(mode="json")
    return success_response(
        request=request,
        message_key="success.lists_retrieved",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload,
    )


@router.get(
    "/{trigger_id}",
    response_model=None,
    responses={
        200: {
            "model": TriggerDetailDataResponse,
            "description": "Trigger retrieved successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Trigger not found"},
        **common_responses,
    },
    summary="Get webhook trigger",
)
async def get_trigger(
    request: Request,
    trigger_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Return a single webhook trigger by ID."""
    service = TriggerService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.get(trigger_id)
    payload = TriggerResponse.model_validate(record)
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
            "model": TriggerDetailDataResponse,
            "description": "Trigger created successfully",
        },
        **common_responses,
    },
    summary="Create webhook trigger",
)
async def create_trigger(
    request: Request,
    body: CreateTriggerRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Create a new webhook trigger."""
    service = TriggerService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.create(body.model_dump(mode="json"))
    payload = TriggerResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.created",
        custom_code=CustomStatusCode.CREATED,
        data=payload.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/{trigger_id}",
    response_model=None,
    responses={
        200: {
            "model": TriggerDetailDataResponse,
            "description": "Trigger updated successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Trigger not found"},
        **common_responses,
    },
    summary="Update webhook trigger",
)
async def update_trigger(
    request: Request,
    trigger_id: str,
    body: UpdateTriggerRequest,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Update an existing webhook trigger."""
    service = TriggerService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    record = await service.update(trigger_id, body.model_dump(exclude_unset=True, mode="json"))
    payload = TriggerResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.delete(
    "/{trigger_id}",
    response_model=None,
    responses={
        200: {
            "model": DeleteIdDataResponse,
            "description": "Trigger deleted successfully",
        },
        404: {"model": NotFoundErrorDoc, "description": "Trigger not found"},
        **common_responses,
    },
    summary="Delete webhook trigger",
)
async def delete_trigger(
    request: Request,
    trigger_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Soft-delete a webhook trigger."""
    service = TriggerService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    deleted_id = await service.delete(trigger_id)
    payload = DeleteIdResponse(id=deleted_id)
    return success_response(
        request=request,
        message_key="success.deleted",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )


@router.post(
    "/{trigger_id}/test",
    response_model=None,
    responses={
        200: {
            "model": TriggerTestDataResponse,
            "description": "Trigger test completed",
        },
        404: {"model": NotFoundErrorDoc, "description": "Trigger not found"},
        **common_responses,
    },
    summary="Test webhook trigger",
)
async def test_trigger(
    request: Request,
    trigger_id: str,
    scope: ApiKeyScope = Depends(get_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
):
    """Send a sample payload to a trigger webhook URL."""
    service = TriggerService(
        db=db,
        tenant_id=scope.tenant_id,
        project_id=scope.project_id,
    )
    result = await service.test(trigger_id, actor=scope.api_key_name)
    payload = TriggerTestResult.model_validate(result)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
