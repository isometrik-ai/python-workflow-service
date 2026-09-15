"""Presigned upload URL schemas."""

from pydantic import BaseModel

from app.core.schemas.responses.base import DataResponse


class PresignedUrlResponse(BaseModel):
    """Presigned upload URL payload."""

    url: str
    file_name: str
    bucket: str


class PresignedUrlDataResponse(DataResponse[PresignedUrlResponse]):
    """Success envelope for presigned URL generation."""
