"""OpenAPI documentation models for common HTTP error responses."""

from typing import Any

from app.core.schemas.responses.base import BaseResponseDoc


class UnauthorizedErrorDoc(BaseResponseDoc):
    """Documentation model for unauthorized errors."""

    status: str = "error"

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "message": "Authentication required",
                "status_code": 401,
                "code": "4001",
            },
        },
    }


class ForbiddenErrorDoc(BaseResponseDoc):
    """Documentation model for forbidden errors."""

    status: str = "error"

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "message": "Insufficient permissions",
                "status_code": 403,
                "code": "4002",
            },
        },
    }


class NotFoundErrorDoc(BaseResponseDoc):
    """Documentation model for not found errors."""

    status: str = "error"

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "message": "Resource not found",
                "status_code": 404,
                "code": "4003",
            },
        },
    }


class ServerErrorDoc(BaseResponseDoc):
    """Documentation model for server errors."""

    status: str = "error"

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "message": "Internal server error",
                "status_code": 500,
                "code": "6000",
            },
        },
    }


class ValidationErrorDoc(BaseResponseDoc):
    """Documentation model for validation errors."""

    status: str = "error"
    errors: list[dict[str, Any]]

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "message": "Validation error",
                "status_code": 422,
                "code": "4004",
                "errors": [
                    {
                        "field": "username",
                        "type": "string_pattern_mismatch",
                        "msg": "String should match pattern '^[a-z0-9]+$'",
                    },
                ],
            },
        },
    }


class ConflictErrorDoc(BaseResponseDoc):
    """Documentation model for conflict errors."""

    status: str = "error"

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "message": "Resource already exists",
                "status_code": 409,
                "code": "4005",
            },
        },
    }


class BadRequestErrorDoc(BaseResponseDoc):
    """Documentation model for bad request errors."""

    status: str = "error"

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "error",
                "message": "Bad request",
                "status_code": 400,
                "code": "4000",
            },
        },
    }
