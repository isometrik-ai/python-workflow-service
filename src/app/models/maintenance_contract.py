"""SQLAlchemy model for maintenance contracts."""

from datetime import date, datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.postgres.database import Base
from app.models.schema import DB_SCHEMA
from app.schemas.common import RecordStatus
from app.schemas.contracts import (
    ContractStatus,
    PaymentFrequency,
    VisitFrequency,
)


class MaintenanceContract(Base):
    """Maintenance contract under a tenant/project."""

    __tablename__ = "maintenance_contracts"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True, unique=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    vendor_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    asset_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    visit_frequency: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VisitFrequency.QUARTERLY.value,
    )
    payment_frequency: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PaymentFrequency.QUARTERLY.value,
    )
    value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ContractStatus.ACTIVE.value,
        index=True,
    )
    next_visit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_serviced_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_generate_lead_days: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    scope_included: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope_excluded: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    documents: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
        server_default=text("'{}'"),
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

    __table_args__ = (
        Index(
            "idx_wo_contracts_tenant_project_status",
            "tenant_id",
            "project_id",
            "record_status",
        ),
        {"schema": DB_SCHEMA},
    )
