"""Reusable OpenAPI response definitions for route documentation."""

from app.core.schemas.responses.error_responses import (
    ForbiddenErrorDoc,
    ServerErrorDoc,
    UnauthorizedErrorDoc,
)

# Common response patterns that can be reused across routes
common_responses = {
    401: {"model": UnauthorizedErrorDoc, "description": "Authentication required"},
    403: {"model": ForbiddenErrorDoc, "description": "Insufficient permissions"},
    500: {"model": ServerErrorDoc, "description": "Internal server error"},
}

# Predefined response sets for different endpoint types
# auth_responses = {
#     400: {"model": BadRequestErrorDoc, "description": "Invalid credentials format"},
#     401: {"model": UnauthorizedErrorDoc, "description": "Invalid credentials"}
# }

# user_responses = {
#     404: {"model": NotFoundErrorDoc, "description": "User not found"},
#     409: {"model": ConflictErrorDoc, "description": "Username or email already exists"},
#     **common_responses
# }
