"""Outbound webhook HTTP client helpers."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from app.core.utils.webhook_url import validate_outbound_webhook_url

WEBHOOK_EVENT_HEADER = "x-webhook-event"
WEBHOOK_SIGNATURE_HEADER = "x-webhook-signature"


def sign_webhook_payload(secret: str, body: bytes) -> str:
    """Return an HMAC-SHA256 signature header value for a webhook body."""
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def post_webhook(
    url: str,
    *,
    secret: str | None,
    event: str,
    payload: dict[str, Any],
    timeout: float = 10.0,
) -> tuple[int | None, str | None]:
    """POST a signed webhook payload and return HTTP status or transport error."""
    cleaned_url = validate_outbound_webhook_url(url)
    body = json.dumps(payload, default=str).encode()
    headers = {
        "content-type": "application/json",
        WEBHOOK_EVENT_HEADER: event,
    }
    if secret:
        headers[WEBHOOK_SIGNATURE_HEADER] = sign_webhook_payload(secret, body)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(cleaned_url, content=body, headers=headers)
        return response.status_code, None
    except httpx.HTTPError as exc:
        return None, f"{type(exc).__name__}: {exc}"
