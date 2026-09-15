"""SQLAlchemy model for tenant-scoped custom field definitions."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.postgres.database import Base
from app.models.schema import DB_SCHEMA
from app.schemas.common import RecordStatus


class CustomField(Base):
    """Custom field definition for assets (global or category-scoped)."""

    __tablename__ = "custom_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, unique=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_key: Mapped[str] = mapped_column(String(128), nullable=False)
    field_type: Mapped[str] = mapped_column(String(32), nullable=False)
    type_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    show_on_create: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_on_detail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="global")
    category_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(f"{DB_SCHEMA}.asset_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
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
            "idx_wo_custom_fields_tenant_project_status",
            "tenant_id",
            "project_id",
            "record_status",
        ),
        {"schema": DB_SCHEMA},
    )
