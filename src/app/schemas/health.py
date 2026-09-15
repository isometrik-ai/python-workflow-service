"""Health check response schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    """Health status of a single dependency service."""

    status: Literal["healthy", "unhealthy", "degraded"]
    type: str | None = None
    error: str | None = None


ServiceHealth = dict[str, dict[str, Any]]


class HealthCheckResponse(BaseModel):
    """Aggregated health check response for the application."""

    status: Literal["healthy", "unhealthy", "degraded"]
    timestamp: str
    version: str
    environment: str
    services: dict[str, ServiceStatus] = Field(default_factory=dict)
