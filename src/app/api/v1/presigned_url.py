"""API routes for presigned upload URLs."""

from fastapi import APIRouter, Depends, Query, Request

from app.business.services.presigned_url_service import PresignedUrlService
from app.core.constants.status_codes import CustomStatusCode
from app.core.schemas.responses import common_responses
from app.core.security.api_key_auth import get_api_key_scope
from app.core.utils.response_factory import success_response
from app.schemas.common import ApiKeyScope
from app.schemas.presigned_url import PresignedUrlDataResponse, PresignedUrlResponse

router = APIRouter(prefix="/upload", tags=["Uploads"])


@router.get(
    "/presigned-url",
    response_model=None,
    responses={
        200: {
            "model": PresignedUrlDataResponse,
            "description": "Presigned upload URL generated successfully",
        },
        **common_responses,
    },
    summary="Generate presigned upload URL",
)
async def get_presigned_url(
    request: Request,
    file_name: str = Query(..., min_length=1, max_length=255),
    path: str = Query(..., description="Path prefix, e.g. tenant-id/project-id/invoices"),
    bucket: str = Query(..., min_length=1, max_length=255),
    content_type: str = Query(..., min_length=1, max_length=255),
    scope: ApiKeyScope = Depends(get_api_key_scope),
):
    """Return a short-lived presigned PUT URL for R2/S3 uploads."""
    _ = scope
    service = PresignedUrlService()
    record = service.generate(
        file_name=file_name,
        path=path,
        bucket=bucket,
        content_type=content_type,
    )
    payload = PresignedUrlResponse.model_validate(record)
    return success_response(
        request=request,
        message_key="presigned_url.success.presigned_url_generated",
        custom_code=CustomStatusCode.SUCCESS,
        data=payload.model_dump(mode="json"),
    )
