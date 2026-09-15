"""Decorator functions for FastAPI endpoints."""

from app.middleware.rate_limiting import limiter


def rate_limit(limit_string: str = None):
    """Apply rate limiting to specific endpoints.

    Parameters
    ----------
    limit_string : str, optional
        Rate limit string in the format "number/period" (e.g., "5/minute", "100/hour").
        If not provided, the default rate limit from settings will be applied.

    Examples:
    --------
    @app.get("/items/")
    @rate_limit("5/minute")
    async def read_items(request: Request):
        return {"items": ["foo", "bar"]}

    """

    def decorator(func):
        # Apply the limiter.limit decorator with the provided limit string
        if limit_string:
            return limiter.limit(limit_string)(func)
        # If no limit string provided, use the default limit with explicit value
        return limiter.limit("60/minute")(func)

    return decorator


def rate_limit_by_key(limit_string: str, key_func):
    """Apply rate limiting based on a custom key.

    Parameters
    ----------
    limit_string : str
        Rate limit string in the format "number/period" (e.g., "5/minute", "100/hour")
    key_func : callable
        Function that takes a request and returns a key for rate limiting

    Examples:
    --------
    def get_user_id(request: Request):
        return request.state.user_id

    @app.get("/user-items/")
    @rate_limit_by_key("10/minute", get_user_id)
    async def read_user_items(request: Request):
        return {"user": request.state.user_id, "items": ["foo", "bar"]}

    """

    def decorator(func):
        return limiter.limit(limit_string, key_func=key_func)(func)

    return decorator
