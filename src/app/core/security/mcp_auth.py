"""Authentication helpers for the MCP JSON-RPC endpoint."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.api_key_service import ApiKeyService
from app.core.db.postgres.database import async_get_db
from app.schemas.common import ApiKeyScope


def _extract_api_key(request: Request) -> str:
    """Extract API key from Authorization Bearer or X-Api-Key header."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return (request.headers.get("x-api-key") or "").strip()


async def get_mcp_api_key_scope(
    request: Request,
    db: AsyncSession = Depends(async_get_db),
) -> ApiKeyScope:
    """Resolve tenant/project scope for MCP using Bearer or X-Api-Key."""
    service = ApiKeyService(db=db)
    return await service.resolve_scope(raw_api_key=_extract_api_key(request))
