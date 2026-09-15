"""Database operations for API call logs."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_call_log import ApiCallLog


class CRUDApiCallLog:
    """CRUD operations for API call logs."""

    async def create(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int = 0,
        source: str | None = None,
        request_body: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist an API call log entry."""
        row = ApiCallLog(
            id=self.new_id(),
            tenant_id=tenant_id,
            project_id=project_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            source=source,
            request_body=request_body or {},
            response_body=response_body or {},
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return _api_call_log_to_dict(row)

    async def list(
        self,
        db: AsyncSession,
        *,
        tenant_id: str,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        limit: int | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List API call logs newest first."""
        filters = [
            ApiCallLog.tenant_id == tenant_id,
            ApiCallLog.project_id == project_id,
        ]
        count_stmt = select(func.count()).select_from(ApiCallLog).where(*filters)
        total = int((await db.execute(count_stmt)).scalar_one())

        effective_limit = min(limit or page_size, 500)
        offset = (page - 1) * page_size if limit is None else 0
        stmt = (
            select(ApiCallLog)
            .where(*filters)
            .order_by(ApiCallLog.at.desc())
            .offset(offset)
            .limit(effective_limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()
        return [_api_call_log_to_dict(row) for row in rows], total

    @staticmethod
    def new_id() -> str:
        """Generate a primary key for new API call log rows."""
        return f"api_call_log_{uuid.uuid4().hex[:12]}"


def _api_call_log_to_dict(row: ApiCallLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "project_id": row.project_id,
        "at": row.at,
        "method": row.method,
        "path": row.path,
        "status_code": row.status_code,
        "duration_ms": row.duration_ms,
        "source": row.source,
        "request_body": row.request_body or {},
        "response_body": row.response_body or {},
    }


crud_api_call_logs = CRUDApiCallLog()
