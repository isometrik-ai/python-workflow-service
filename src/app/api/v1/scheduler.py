"""API routes for on-demand scheduler runs."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.scheduler_service import SchedulerService
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.schemas.responses import common_responses
from app.core.security.internal_auth import get_scheduler_auth
from app.core.utils.response_factory import success_response
from app.schemas.common import ApiKeyScope
from app.schemas.triggers import SchedulerRunDataResponse, SchedulerRunResult

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.post(
    "/run",
    response_model=None,
    responses={
        200: {
            "model": SchedulerRunDataResponse,
            "description": "Scheduler run completed",
        },
        **common_responses,
    },
    summary="Run work order scheduler",
)
async def run_scheduler(
    request: Request,
    scope: ApiKeyScope | None = Depends(get_scheduler_auth),
    db: AsyncSession = Depends(async_get_db),
):
    """Generate due contract and recurring work orders.

    Accepts either internal service token (all tenants) or API key scope (single tenant).
    """
    service = SchedulerService(db=db)
    tenant_id = scope.tenant_id if scope else None
    result = await service.run_once(tenant_id)
    payload = SchedulerRunResult.model_validate(result)
    return success_response(
        request=request,
        message_key="success.updated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
