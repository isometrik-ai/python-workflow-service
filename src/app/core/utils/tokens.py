"""Vendor portal token utilities."""

from __future__ import annotations

import hashlib
import secrets


def generate_vendor_token() -> tuple[str, str]:
    """Generate a raw vendor token and its SHA-256 hash."""
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_vendor_token(raw: str) -> str:
    """Return the SHA-256 hex digest of a raw vendor token."""
    return hashlib.sha256(raw.encode()).hexdigest()
