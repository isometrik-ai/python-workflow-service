"""HTTP exception types with i18n message keys and custom status codes."""

from fastapi import HTTPException, status

from app.core.constants.status_codes import CustomStatusCode


class CustomHTTPException(HTTPException):
    """Custom HTTP exception with message key for translations."""

    def __init__(
        self,
        status_code: int,
        message_key: str,
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.VALIDATION_ERROR,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize the exception with HTTP status, message key, and optional metadata."""
        self.message_key = message_key
        self.custom_code = custom_code
        self.params = params
        self.errors = errors
        super().__init__(status_code=status_code, headers=headers)


class ValidationException(CustomHTTPException):
    """Exception raised for validation errors with support for custom code and params."""

    def __init__(
        self,
        message_key: str,
        status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.VALIDATION_ERROR,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize a validation error with message key and field-level errors."""
        super().__init__(
            status_code=status_code,
            message_key=message_key,
            custom_code=custom_code,
            headers=headers,
            errors=errors,
            params=params,
        )


class ServerErrorException(HTTPException):
    """Exception raised for server errors."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        message_key: str = "server_error",
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.SERVER_ERROR,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize a server error response with translation metadata."""
        self.status_code = status_code
        self.message_key = message_key
        self.headers = headers
        self.custom_code = custom_code
        self.params = params
        self.errors = errors
        super().__init__(
            status_code=self.status_code,
            headers=self.headers,
        )


class BadRequestException(HTTPException):
    """Exception raised for bad requests."""

    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        detail: str = "Bad request",
        message_key: str = "bad_request",
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.BAD_REQUEST,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize a bad request error with detail and translation metadata."""
        self.status_code = status_code
        self.detail = detail
        self.message_key = message_key
        self.headers = headers
        self.custom_code = custom_code
        self.params = params
        self.errors = errors
        super().__init__(status_code=self.status_code, detail=self.detail, headers=self.headers)


class UnauthorizedException(HTTPException):
    """Exception raised for unauthorized access."""

    def __init__(
        self,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
        detail: str = "Unauthorized",
        message_key: str = "unauthorized",
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.UNAUTHORIZED,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize an unauthorized error with detail and translation metadata."""
        self.status_code = status_code
        self.detail = detail
        self.message_key = message_key
        self.headers = headers
        self.custom_code = custom_code
        self.params = params
        self.errors = errors
        super().__init__(status_code=self.status_code, detail=self.detail, headers=self.headers)


class ForbiddenException(HTTPException):
    """Exception raised for forbidden access."""

    def __init__(
        self,
        status_code: int = status.HTTP_403_FORBIDDEN,
        detail: str = "Forbidden",
        message_key: str = "forbidden",
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.FORBIDDEN,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize a forbidden error with detail and translation metadata."""
        self.status_code = status_code
        self.detail = detail
        self.message_key = message_key
        self.headers = headers
        self.custom_code = custom_code
        self.params = params
        self.errors = errors
        super().__init__(
            status_code=self.status_code,
            detail=self.detail,
            headers=self.headers,
        )


class NotFoundException(HTTPException):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        status_code: int = status.HTTP_404_NOT_FOUND,
        detail: str = "Not found",
        message_key: str = "not_found",
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.NOT_FOUND,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize a not-found error with detail and translation metadata."""
        self.status_code = status_code
        self.detail = detail
        self.message_key = message_key
        self.headers = headers
        self.custom_code = custom_code
        self.params = params
        self.errors = errors
        super().__init__(
            status_code=self.status_code,
            detail=self.detail,
            headers=self.headers,
        )


class DuplicateValueException(CustomHTTPException):
    """Exception raised when a duplicate value is detected."""

    def __init__(
        self,
        message_key: str = "duplicate_value",
        status_code: int = status.HTTP_409_CONFLICT,
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.DUPLICATE_ENTRY,
        params: dict = None,
        errors: list[dict] = None,
    ):
        """Initialize a duplicate-value conflict with message key and metadata."""
        super().__init__(
            status_code=status_code,
            message_key=message_key,
            headers=headers,
            custom_code=custom_code,
            params=params,
            errors=errors,
        )


class RateLimitExceededException(CustomHTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message_key: str = "rate_limit_exceeded",
        status_code: int = status.HTTP_429_TOO_MANY_REQUESTS,
        headers: dict = None,
        custom_code: CustomStatusCode = CustomStatusCode.RATE_LIMIT_EXCEEDED,
        params: dict = None,
        errors: list[dict] = None,
        retry_after: int = 60,
    ):
        """Initialize a rate-limit error with retry metadata and response headers."""
        self.retry_after = retry_after
        if headers is None:
            headers = {"Retry-After": str(retry_after)}
        else:
            headers["Retry-After"] = str(retry_after)

        if params is None:
            params = {"retry_after": retry_after}

        super().__init__(
            status_code=status_code,
            message_key=message_key,
            headers=headers,
            custom_code=custom_code,
            params=params,
            errors=errors,
        )
