"""Timeline event helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def new_timeline_event(event: dict[str, Any]) -> dict[str, Any]:
    """Build a server-owned timeline event with id and timestamp."""
    return {
        "id": str(uuid4()),
        "at": datetime.now(UTC).isoformat(),
        **event,
    }
