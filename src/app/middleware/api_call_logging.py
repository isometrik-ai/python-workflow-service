"""Middleware that logs POST /api/mcp requests to api_call_logs."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.business.services.api_key_service import ApiKeyService
from app.business.services.log_service import LogService
from app.core.db.postgres.database import async_session_maker
from app.core.security.mcp_auth import _extract_api_key

logger = logging.getLogger(__name__)


def _parse_json_object(raw: bytes) -> dict[str, Any]:
    """Parse bytes as JSON object, falling back to a truncated raw string."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return {"raw": raw.decode("utf-8", errors="replace")[:2000]}


async def _read_response_body(response: Response) -> tuple[bytes, dict[str, Any]]:
    """Collect the full response body and a JSON object representation."""
    response_chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        response_chunks.append(chunk)
    body_bytes = b"".join(response_chunks)
    return body_bytes, _parse_json_object(body_bytes)


class ApiCallLogMiddleware(BaseHTTPMiddleware):
    """Persist MCP API call logs after each POST /api/mcp request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Log MCP POST requests with request/response bodies and timing."""
        if request.method != "POST" or request.url.path != "/api/mcp":
            return await call_next(request)

        start = time.perf_counter()
        body_bytes = await request.body()
        wrapped_request = Request(
            request.scope,
            lambda: {"type": "http.request", "body": body_bytes, "more_body": False},
        )
        response = await call_next(wrapped_request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        response_body_bytes, response_body = await _read_response_body(response)

        await self._persist_log(
            request=wrapped_request,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_body=_parse_json_object(body_bytes),
            response_body=response_body,
        )

        return Response(
            content=response_body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    async def _persist_log(
        self,
        *,
        request: Request,
        status_code: int,
        duration_ms: int,
        request_body: dict[str, Any],
        response_body: dict[str, Any],
    ) -> None:
        """Write the API call log row when scope can be resolved."""
        try:
            async with async_session_maker() as db:
                service = ApiKeyService(db=db)
                scope = await service.resolve_scope(raw_api_key=_extract_api_key(request))
                log_service = LogService(
                    db=db,
                    tenant_id=scope.tenant_id,
                    project_id=scope.project_id,
                )
                await log_service.record_api_call(
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    source=scope.api_key_name or "mcp",
                    request_body=request_body,
                    response_body=response_body,
                )
                await db.commit()
        except Exception as exc:
            logger.warning("Failed to persist API call log: %s", exc)
