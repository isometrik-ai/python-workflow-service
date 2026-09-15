"""SQLAlchemy model for outbound webhook trigger configuration."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.postgres.database import Base
from app.models.schema import DB_SCHEMA
from app.schemas.common import RecordStatus


class TriggerConfig(Base):
    """Outbound webhook trigger configuration."""

    __tablename__ = "trigger_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, unique=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    webhook_url: Mapped[str] = mapped_column(Text, nullable=False)
    secret: Mapped[str | None] = mapped_column(String(500), nullable=True)
    record_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RecordStatus.ACTIVE.value,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index(
            "idx_wo_trigger_configs_tenant_project_status",
            "tenant_id",
            "project_id",
            "record_status",
        ),
        {"schema": DB_SCHEMA},
    )
