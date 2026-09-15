"""SQLAlchemy model for tenant business profile (singleton per tenant/project)."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.postgres.database import Base
from app.models.schema import DB_SCHEMA


class BusinessProfile(Base):
    """Company identity used to populate PDF templates and documents."""

    __tablename__ = "business_profile"

    id: Mapped[str] = mapped_column(String, primary_key=True, default="default")
    tenant_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    legal_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    gstin: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    address_line: Mapped[str] = mapped_column(Text, nullable=False, default="")
    city: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    pincode: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    website: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    logo: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    bank_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    bank_account: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    bank_ifsc: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    default_wo_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_wo_terms: Mapped[str] = mapped_column(Text, nullable=False, default="")
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
        UniqueConstraint("tenant_id", "project_id", name="uq_wo_business_profile_tenant_project"),
        Index("idx_wo_business_profile_tenant_project", "tenant_id", "project_id"),
        {"schema": DB_SCHEMA},
    )
