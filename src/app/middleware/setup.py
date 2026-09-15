"""Setup functions for FastAPI middleware."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.core.config.app_config import settings
from app.middleware.api_call_logging import ApiCallLogMiddleware
from app.middleware.rate_limiting import limiter
from app.middleware.security import SecurityHeadersMiddleware


def setup_middlewares(app: FastAPI) -> None:
    """Configure and add middleware to the FastAPI application.

    This function sets up CORS, rate limiting, and security headers middleware.
    """
    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup SlowAPI rate limiting
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Log MCP API calls
    app.add_middleware(ApiCallLogMiddleware)
