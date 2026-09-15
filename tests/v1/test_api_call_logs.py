"""Tests for API call logs."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from app.core.security.api_key_auth import get_api_key_scope
from app.schemas.common import ApiKeyScope

API_CALL_LOGS_BASE = "/api/v1/api-call-logs"


def iso_timestamp() -> str:
    """Return a stable ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def api_call_log_record(**overrides) -> dict:
    """Build a sample API call log record."""
    payload = {
        "id": "api_call_log_abc123",
        "tenant_id": "tenant123",
        "project_id": "project123",
        "at": iso_timestamp(),
        "method": "POST",
        "path": "/api/mcp",
        "status_code": 200,
        "duration_ms": 42,
        "source": "Integration Key",
        "request_body": {"method": "tools/list"},
        "response_body": {"jsonrpc": "2.0", "result": {}},
    }
    payload.update(overrides)
    return payload


@pytest.fixture(scope="function", autouse=True)
def override_dependencies(client):
    """Override API key scope dependency."""
    scope = ApiKeyScope(
        tenant_id="tenant123",
        project_id="project123",
        api_key_id="key-1",
        api_key_name="Integration Key",
    )
    overrides = client.app.dependency_overrides.copy()
    client.app.dependency_overrides[get_api_key_scope] = lambda: scope
    yield
    client.app.dependency_overrides.clear()
    client.app.dependency_overrides.update(overrides)


def test_list_api_call_logs_success(client):
    """List API call logs returns paginated envelope."""
    patcher = patch("app.api.v1.logs.LogService")
    service_cls = patcher.start()
    instance = MagicMock()
    instance.list_api_call_logs = AsyncMock(return_value=([api_call_log_record()], 1))
    service_cls.return_value = instance
    try:
        response = client.get(API_CALL_LOGS_BASE)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"][0]["path"] == "/api/mcp"
    finally:
        patcher.stop()
