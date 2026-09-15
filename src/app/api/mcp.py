"""MCP JSON-RPC 2.0 server for work-order domain tools."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.business.services.mcp_service import McpService, json_safe, mcp_tools
from app.core.db.postgres.database import async_get_db
from app.core.security.mcp_auth import get_mcp_api_key_scope
from app.schemas.common import ApiKeyScope

router = APIRouter(prefix="/mcp", tags=["MCP"])


def _jsonrpc_result(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _jsonrpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


async def _handle_tools_call(
    *,
    msg_id: Any,
    params: dict[str, Any],
    scope: ApiKeyScope,
    db: AsyncSession,
) -> dict[str, Any]:
    """Execute an MCP tools/call request."""
    name = params.get("name", "")
    args = params.get("arguments") or {}
    service = McpService(db=db, scope=scope)
    try:
        data = await service.call_tool(name, args)
        return _jsonrpc_result(
            msg_id,
            {"content": [{"type": "text", "text": json.dumps(json_safe(data), default=str)}]},
        )
    except HTTPException as exc:
        return _jsonrpc_error(msg_id, -32000, str(exc.detail))
    except Exception as exc:
        return _jsonrpc_error(msg_id, -32000, str(exc))


@router.post("")
async def mcp_handler(
    request: Request,
    scope: ApiKeyScope = Depends(get_mcp_api_key_scope),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, Any]:
    """Handle stateless JSON-RPC 2.0 MCP requests."""
    try:
        message = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Body must be JSON") from exc

    method = message.get("method")
    msg_id = message.get("id")
    params = message.get("params") or {}

    static_handlers: dict[str, Callable[[], dict[str, Any]]] = {
        "initialize": lambda: _jsonrpc_result(
            msg_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "work-order-service", "version": "1.0.0"},
            },
        ),
        "notifications/initialized": lambda: {"jsonrpc": "2.0", "result": {}},
        "tools/list": lambda: _jsonrpc_result(msg_id, {"tools": mcp_tools()}),
    }
    if method in static_handlers:
        return static_handlers[method]()

    if method == "tools/call":
        return await _handle_tools_call(msg_id=msg_id, params=params, scope=scope, db=db)

    return _jsonrpc_error(msg_id, -32601, f"Method not found: {method}")


@router.get("")
async def mcp_docs() -> dict[str, Any]:
    """Return MCP server documentation."""
    return {
        "server": "work-order-service MCP",
        "transport": "HTTP (stateless JSON-RPC 2.0)",
        "endpoint": "/api/mcp",
        "auth": "Authorization: Bearer <api-key> or X-Api-Key",
        "methods": ["initialize", "tools/list", "tools/call"],
    }
