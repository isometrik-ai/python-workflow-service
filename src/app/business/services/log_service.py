"""Audit and webhook delivery log business logic."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_api_call_logs import crud_api_call_logs
from app.crud.crud_audit_events import crud_audit_events
from app.crud.crud_webhook_deliveries import crud_webhook_deliveries


class LogService:
    """Read-only log queries scoped to tenant/project."""

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: str,
        project_id: str,
    ) -> None:
        """Initialize the service with database session and tenant scope."""
        self.db = db
        self.tenant_id = tenant_id
        self.project_id = project_id

    async def list_audit_events(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        entity: str | None = None,
        entity_id: str | None = None,
        source: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated audit events for the tenant/project."""
        return await crud_audit_events.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            entity=entity,
            entity_id=entity_id,
            source=source,
        )

    async def list_webhook_deliveries(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated webhook delivery logs for the tenant/project."""
        return await crud_webhook_deliveries.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
        )

    async def list_api_call_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        limit: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return paginated API call logs for the tenant/project."""
        return await crud_api_call_logs.list(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            page=page,
            page_size=page_size,
            limit=limit,
        )

    async def record_api_call(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int = 0,
        source: str | None = None,
        request_body: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist an API call log entry."""
        return await crud_api_call_logs.create(
            self.db,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            source=source,
            request_body=request_body,
            response_body=response_body,
        )
