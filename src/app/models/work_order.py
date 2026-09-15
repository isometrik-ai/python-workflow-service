"""SQLAlchemy model for work orders."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.postgres.database import Base
from app.models.schema import DB_SCHEMA
from app.schemas.common import RecordStatus
from app.schemas.work_orders import WorkOrderPriority, WorkOrderSource, WorkOrderState


class WorkOrder(Base):
    """Work order under a tenant/project."""

    __tablename__ = "work_orders"
    __table_args__ = (
        Index(
            "idx_wo_work_orders_tenant_project_status",
            "tenant_id",
            "project_id",
            "record_status",
        ),
        Index(
            "idx_wo_work_orders_vendor_token",
            "vendor_token_hash",
            postgresql_where=text("vendor_token_hash IS NOT NULL"),
        ),
        {"schema": DB_SCHEMA},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, unique=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
    )
    contract_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(f"{DB_SCHEMA}.maintenance_contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    form_template_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(f"{DB_SCHEMA}.form_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    pre_start_form_template_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(f"{DB_SCHEMA}.form_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=WorkOrderState.UPCOMING.value,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=WorkOrderPriority.MEDIUM.value,
    )
    source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=WorkOrderSource.AD_HOC.value,
    )
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assignee_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    line_items: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    form_values: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    pre_start_form_values: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    estimated_cost: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    access_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_recurring: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recurring_frequency: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recurring_days: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    recurring_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recurring_parent_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey(f"{DB_SCHEMA}.work_orders.id", ondelete="SET NULL"),
        nullable=True,
    )
    recurring_next_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
    )
    vendor_token_hash: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    timeline: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
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
