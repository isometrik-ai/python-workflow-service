"""API key hashing helpers."""

from __future__ import annotations

import hashlib
import secrets

MIN_API_KEY_LENGTH = 16


def hash_api_key(raw: str) -> str:
    """Return the SHA-256 hex digest of a raw API key."""
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate a raw API key, its hash, and a display prefix."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_api_key(raw), raw[:12]
