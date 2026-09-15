"""Internal service token authentication."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.api_key_service import ApiKeyService
from app.core.config.app_config import settings
from app.core.constants.status_codes import CustomStatusCode
from app.core.db.postgres.database import async_get_db
from app.core.exceptions.http_exceptions import UnauthorizedException
from app.core.utils.header_validators import (
    HeaderInternalAuth,
    HeaderSchedulerAuth,
    get_header_internal_auth,
    get_header_scheduler_auth,
)
from app.schemas.common import ApiKeyScope


async def require_internal_token(
    headers: HeaderInternalAuth = Depends(get_header_internal_auth),
) -> None:
    """Validate the internal service token from request headers."""
    internal = settings.WOM_INTERNAL_SERVICE_TOKEN
    if not internal:
        raise UnauthorizedException(
            message_key="api_keys.errors.internal_token_required",
            custom_code=CustomStatusCode.UNAUTHORIZED,
        )
    if (headers.x_internal_token or "").strip() != internal.strip():
        raise UnauthorizedException(
            message_key="api_keys.errors.invalid_internal_token",
            custom_code=CustomStatusCode.UNAUTHORIZED,
        )


async def get_scheduler_auth(
    headers: HeaderSchedulerAuth = Depends(get_header_scheduler_auth),
    db: AsyncSession = Depends(async_get_db),
) -> ApiKeyScope | None:
    """Resolve scheduler auth via internal token or API key scope."""
    internal = settings.WOM_INTERNAL_SERVICE_TOKEN
    if internal and (headers.x_internal_token or "").strip() == internal.strip():
        return None
    service = ApiKeyService(db=db)
    return await service.resolve_scope(
        raw_api_key=headers.x_api_key,
        tenant_id=headers.x_tenant_id,
        project_id=headers.x_project_id,
    )
