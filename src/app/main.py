"""Main FastAPI application entry point."""

import os

import uvicorn

from app.api import router
from app.core.config.app_config import settings
from app.core.setup import create_application

# from app.core.services.cache_maintenance import start_cache_maintenance

port_value = int(os.environ.get("PORT", "8000"))
reload_enabled = os.environ.get("RELOAD", "false").lower() == "true"

_UVICORN_LOG_LEVELS = frozenset({"critical", "error", "warning", "info", "debug", "trace"})


def _uvicorn_log_level() -> str:
    """Map application log level to a valid uvicorn log level."""
    raw = (settings.LOG_LEVEL or "info").lower()
    return raw if raw in _UVICORN_LOG_LEVELS else "info"


app = create_application(router=router, settings=settings)

if __name__ == "__main__":
    # Start cache maintenance background task
    # start_cache_maintenance()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port_value,
        reload=reload_enabled,
        reload_dirs=["app"] if reload_enabled else None,
        log_level=_uvicorn_log_level(),
    )
