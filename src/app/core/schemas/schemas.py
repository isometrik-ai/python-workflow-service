"""Shared Pydantic schemas used across the application."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class HealthCheck(BaseModel):
    """Health check payload returned by the service status endpoint."""

    name: str
    version: str
    description: str


class TimestampSchema(BaseModel):
    """Mixin schema with ISO-formatted created and updated timestamps."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = Field(default=None)

    @field_serializer("created_at")
    def serialize_created_at(self, created_at: datetime | None, _info: Any) -> str | None:
        """Serialize created_at to an ISO 8601 string."""
        if created_at is None:
            return None
        return created_at.isoformat()

    @field_serializer("updated_at")
    def serialize_updated_at(self, updated_at: datetime | None, _info: Any) -> str | None:
        """Serialize updated_at to an ISO 8601 string."""
        if updated_at is None:
            return None
        return updated_at.isoformat()
