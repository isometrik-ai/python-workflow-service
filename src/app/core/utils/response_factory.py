"""Helpers for building standardized JSON API responses."""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.constants.status_codes import CustomStatusCode
from app.core.i18n.translations import translator
from app.core.schemas.responses.base import (
    ApiResponse,
    DataResponse,
    ErrorResponse,
    ListResponse,
    ResponseStatus,
)

T = TypeVar("T")


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime and Decimal values in API responses."""

    def default(self, o):
        """Encode datetime and Decimal values for JSON serialization."""
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def success_response(
    request: Request,
    message_key: str,
    status_code: int = 200,
    custom_code: CustomStatusCode = CustomStatusCode.SUCCESS,
    data: Any = None,
    params: dict[str, Any] | None = None,
) -> JSONResponse:
    """Create a standard success response."""
    # Get language from request
    language = request.headers.get("lan", "en")

    # Translate message
    message = translator.get(message_key, language, **(params or {}))

    # Create response based on whether data is provided
    if data is not None:
        response_model = DataResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            status_code=status_code,
            code=custom_code,
            data=data,
        )
    else:
        response_model = ApiResponse(
            status=ResponseStatus.SUCCESS,
            message=message,
            status_code=status_code,
            code=custom_code,
        )

    # Use custom encoder for JSON serialization
    response_content = json.loads(json.dumps(response_model.model_dump(), cls=DateTimeEncoder))

    return JSONResponse(status_code=status_code, content=response_content)


def error_response(
    request: Request,
    message_key: str,
    status_code: int = 400,
    custom_code: CustomStatusCode = CustomStatusCode.BAD_REQUEST,
    errors: list[dict[str, Any]] | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create a standard error response."""
    # Get language from request
    language = request.headers.get("lan", "en")

    # Translate message
    message = translator.get(message_key, language, **(params or {}))

    response_model = ErrorResponse(
        status=ResponseStatus.ERROR,
        message=message,
        status_code=status_code,
        code=custom_code,
        errors=errors,
    )

    # Use custom encoder for JSON serialization
    response_content = json.loads(
        json.dumps(response_model.model_dump(exclude_none=True), cls=DateTimeEncoder)
    )

    return JSONResponse(
        status_code=status_code,
        content=response_content,
        headers=headers,
    )


def list_response(
    request: Request,
    items: list[Any],
    total: int,
    *,
    message_key: str = "success.retrieved",
    page: int = 1,
    page_size: int = 10,
    status_code: int = 200,
    custom_code: CustomStatusCode = CustomStatusCode.SUCCESS,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create a standard paginated list response."""
    # Get language from request
    language = request.headers.get("lan", "en")

    # Translate message
    message = translator.get(message_key, language, **(params or {}))

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    has_next = page < total_pages
    has_previous = page > 1

    response_model = ListResponse(
        status=ResponseStatus.SUCCESS,
        message=message,
        status_code=status_code,
        code=custom_code,
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous,
    )

    # Use custom encoder for JSON serialization
    response_content = json.loads(json.dumps(response_model.model_dump(), cls=DateTimeEncoder))

    return JSONResponse(status_code=status_code, content=response_content, headers=headers)
