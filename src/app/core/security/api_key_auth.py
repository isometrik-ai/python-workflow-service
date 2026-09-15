"""API key authentication for staff routes."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.api_key_service import ApiKeyService
from app.core.db.postgres.database import async_get_db
from app.core.utils.header_validators import HeaderApiKeyAuth, get_header_api_key_auth
from app.schemas.common import ApiKeyScope


async def get_api_key_scope(
    headers: HeaderApiKeyAuth = Depends(get_header_api_key_auth),
    db: AsyncSession = Depends(async_get_db),
) -> ApiKeyScope:
    """Resolve tenant/project scope from API key or tenant/project headers."""
    service = ApiKeyService(db=db)
    return await service.resolve_scope(
        raw_api_key=headers.x_api_key,
        tenant_id=headers.x_tenant_id,
        project_id=headers.x_project_id,
    )


get_api_key_context = get_api_key_scope
