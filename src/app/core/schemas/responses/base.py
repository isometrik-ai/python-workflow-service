"""Base Pydantic models for API response envelopes."""

from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.constants.status_codes import CustomStatusCode


class ResponseStatus(str, Enum):
    """High-level outcome status included in every API response."""

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


T = TypeVar("T")


class BaseResponseDoc(BaseModel):
    """Base class for response documentation models."""

    status: str
    message: str
    status_code: int
    code: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Operation successful",
                "status_code": 200,
                "code": "2000",
            },
        },
    }


class ApiResponse(BaseModel):
    """Base response model for all API responses."""

    status: ResponseStatus = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    status_code: int = Field(..., description="HTTP status code")
    code: CustomStatusCode = Field(..., description="Custom status code")


class DataResponse(ApiResponse, Generic[T]):
    """Response model that includes data."""

    data: T = Field(None, description="Response data")


class ListResponse(ApiResponse):
    """Response model for list data with pagination."""

    data: list[Any] = Field([], description="List of items")
    total: int = Field(0, description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(10, description="Number of items per page")
    total_pages: int = Field(0, description="Total number of pages")
    has_next: bool = Field(False, description="Whether there are more pages")
    has_previous: bool = Field(False, description="Whether there are previous pages")


class ErrorResponse(ApiResponse):
    """Response model for errors with additional details."""

    errors: list[dict[str, Any]] | None = Field(
        None,
        description="Detailed error information",
    )
