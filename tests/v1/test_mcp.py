"""Minimal tests for MCP JSON-RPC endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.mcp_auth import get_mcp_api_key_scope
from app.schemas.common import ApiKeyScope

MCP_BASE = "/api/mcp"


@pytest.fixture(scope="function", autouse=True)
def override_mcp_auth(client):
    """Override MCP API key scope dependency."""
    scope = ApiKeyScope(
        tenant_id="tenant123",
        project_id="project123",
        api_key_id="key-1",
        api_key_name="Integration Key",
    )
    overrides = client.app.dependency_overrides.copy()
    client.app.dependency_overrides[get_mcp_api_key_scope] = lambda: scope
    yield
    client.app.dependency_overrides.clear()
    client.app.dependency_overrides.update(overrides)


def test_mcp_docs(client):
    """GET /api/mcp returns server documentation."""
    response = client.get(MCP_BASE)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["endpoint"] == "/api/mcp"


def test_mcp_tools_list(client):
    """POST tools/list returns tool definitions."""
    response = client.post(MCP_BASE, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"]["tools"]
    tool_names = {tool["name"] for tool in body["result"]["tools"]}
    assert "list_work_orders" in tool_names
    assert "get_business_profile" in tool_names


def test_mcp_initialize(client):
    """POST initialize returns protocol info."""
    response = client.post(MCP_BASE, json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"]["serverInfo"]["name"] == "work-order-service"


def test_mcp_tools_call_get_business_profile(client):
    """POST tools/call get_business_profile delegates to service."""
    patcher = patch("app.api.mcp.McpService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.call_tool = AsyncMock(return_value={"name": "Acme FM"})
    service_cls.return_value = instance
    try:
        response = client.post(
            MCP_BASE,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "get_business_profile", "arguments": {}},
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert "Acme FM" in response.json()["result"]["content"][0]["text"]
    finally:
        patcher.stop()
