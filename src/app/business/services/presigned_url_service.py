"""Presigned R2/S3 upload URL generation."""

from __future__ import annotations

import boto3
from botocore.config import Config

from app.core.config.app_config import settings
from app.core.constants.status_codes import CustomStatusCode
from app.core.exceptions.http_exceptions import ServerErrorException


class PresignedUrlService:
    """Generate short-lived presigned PUT URLs for file uploads."""

    def __init__(self) -> None:
        """Initialize R2 credentials from application settings."""
        self._account_id = settings.R2_ACCOUNT_ID
        self._access_key = settings.R2_ACCESS_KEY
        self._secret_key = settings.R2_SECRET_KEY

    def _get_r2_client(self):
        if not self._access_key or not self._secret_key or not self._account_id:
            raise ServerErrorException(
                message_key="presigned_url.errors.r2_credentials_not_configured",
                custom_code=CustomStatusCode.SERVER_ERROR,
            )
        endpoint = f"https://{self._account_id}.r2.cloudflarestorage.com"
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    def generate(
        self,
        *,
        file_name: str,
        path: str,
        bucket: str,
        content_type: str,
        expires_in: int = 300,
    ) -> dict[str, str]:
        """Generate a short-lived presigned PUT URL for file upload."""
        client = self._get_r2_client()
        path_clean = path.strip("/")
        file_key = f"{path_clean}/{file_name}" if path_clean else file_name
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": file_key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )
        return {
            "url": url,
            "file_name": file_name,
            "bucket": bucket,
        }
