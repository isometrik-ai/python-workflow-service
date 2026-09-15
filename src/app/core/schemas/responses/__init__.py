"""Shared API response models and OpenAPI error documentation."""

from app.core.schemas.responses.base import (
    ApiResponse,
    DataResponse,
    ErrorResponse,
    ListResponse,
    ResponseStatus,
)
from app.core.schemas.responses.error_responses import (
    ConflictErrorDoc,
    ForbiddenErrorDoc,
    NotFoundErrorDoc,
    ServerErrorDoc,
    UnauthorizedErrorDoc,
)

# Common response patterns
common_responses = {
    401: {"model": UnauthorizedErrorDoc, "description": "Authentication required"},
    403: {"model": ForbiddenErrorDoc, "description": "Insufficient permissions"},
    500: {"model": ServerErrorDoc, "description": "Internal server error"},
}

# Re-export everything
__all__ = [
    "ApiResponse",
    "ConflictErrorDoc",
    "DataResponse",
    "ErrorResponse",
    "ForbiddenErrorDoc",
    "ListResponse",
    "NotFoundErrorDoc",
    "ResponseStatus",
    "ServerErrorDoc",
    "UnauthorizedErrorDoc",
    "common_responses",
]
