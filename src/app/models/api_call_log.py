"""SQLAlchemy model for API call audit logs (MCP and integrations)."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.postgres.database import Base
from app.models.schema import DB_SCHEMA


class ApiCallLog(Base):
    """Log entry for external API/MCP calls."""

    __tablename__ = "api_call_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, unique=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True,
    )
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(256), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_body: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    response_body: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    __table_args__ = (
        Index(
            "idx_wo_api_call_logs_tenant_project_at",
            "tenant_id",
            "project_id",
            "at",
        ),
        {"schema": DB_SCHEMA},
    )
