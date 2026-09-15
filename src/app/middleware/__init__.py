"""Middleware components for the FastAPI application.

This module contains middleware for rate limiting, CORS, and other cross-cutting concerns.
"""

from app.middleware.rate_limiting import get_limiter, limiter
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.setup import setup_middlewares

__all__ = ["limiter", "get_limiter", "SecurityHeadersMiddleware", "setup_middlewares"]
