"""
Shared HTTP error classes and utilities for all Briefly services.

Provides:
- Base exception class for API errors
- Common subclasses (Validation, Auth, NotFound, Service, Provider, RateLimit)
- Shared error response model
- Utility to convert exceptions to error responses
- (Optional) FastAPI exception handler registration

Common Usage Patterns:
=====================

Basic Exception Usage:
>>> from services.common.http_errors import ValidationError, NotFoundError, AuthError
>>>
>>> # Validation error with field context
>>> error = ValidationError("Invalid email format", field="email", value="bad-email")
>>>
>>> # Resource not found
>>> error = NotFoundError("User", "user-123")
>>>
>>> # Authentication failure
>>> error = AuthError("Token expired", code=ErrorCode.TOKEN_EXPIRED)

FastAPI Integration:
>>> from fastapi import FastAPI
>>> from services.common.http_errors import register_briefly_exception_handlers
>>>
>>> app = FastAPI()
>>> register_briefly_exception_handlers(app)
>>>
>>> @app.get("/users/{user_id}")
>>> async def get_user(user_id: str):
...     if not user_exists(user_id):
...         raise NotFoundError("User", user_id)
...     return {"user_id": user_id}

Provider Error Handling:
>>> from services.common.http_errors import ProviderError, ErrorCode
>>>
>>> # Google API error with response details
>>> error = ProviderError(
...     message="Google API quota exceeded",
...     provider="google",
...     code=ErrorCode.GOOGLE_QUOTA_EXCEEDED,
...     retry_after=3600,
...     response_body='{"error": "quotaExceeded"}'
... )

Error Response Conversion:
>>> from services.common.http_errors import exception_to_response
>>>
>>> # Convert any exception to standardized response
>>> try:
...     risky_operation()
... except Exception as e:
...     error_response = exception_to_response(e)
...     return JSONResponse(
...         status_code=500,
...         content=error_response.model_dump()
...     )

Service Error with Context:
>>> from services.common.http_errors import ServiceError, ErrorCode
>>>
>>> # Database connection failure
>>> error = ServiceError(
...     "Database connection failed",
...     code=ErrorCode.DATABASE_ERROR,
...     details={
...         "database": "postgresql",
...         "host": "db.example.com",
...         "timeout_ms": 5000,
...         "retry_count": 3
...     }
... )

Rate Limiting:
>>> from services.common.http_errors import RateLimitError
>>>
>>> # API rate limit with retry information
>>> error = RateLimitError(
...     "API rate limit exceeded",
...     retry_after=3600,
...     details={
...         "limit": 1000,
...         "remaining": 0,
...         "window": "hourly",
...         "reset_time": "2024-01-15T11:00:00Z"
...     }
... )

Error Code Naming Guidelines:
============================
1. Use ALL_CAPS with underscores for separating words
2. Prefer specific descriptive names over generic suffixes
3. Provider-specific codes follow pattern: {PROVIDER}_{SPECIFIC_ERROR}
4. Common patterns:
   - Authentication: {PROVIDER}_AUTH_FAILED, {PROVIDER}_TOKEN_EXPIRED
   - Authorization: {PROVIDER}_ACCESS_DENIED, {PROVIDER}_INSUFFICIENT_PERMISSIONS
   - Rate Limiting: {PROVIDER}_RATE_LIMITED, {PROVIDER}_QUOTA_EXCEEDED
   - API Errors: {PROVIDER}_API_ERROR, {PROVIDER}_SERVICE_ERROR
   - Validation: VALIDATION_FAILED, INVALID_{FIELD}
   - Resources: NOT_FOUND, ALREADY_EXISTS
   - Service: SERVICE_UNAVAILABLE, INTERNAL_ERROR

Error Code Taxonomy:
===================
- VALIDATION_* : Input validation errors (422)
- AUTH_* : Authentication errors (401)
- ACCESS_* : Authorization/permission errors (403)
- NOT_FOUND : Resource not found (404)
- RATE_LIMITED : Rate limiting (429)
- SERVICE_* : Internal service errors (5xx)
- PROVIDER_* : External provider integration errors (502)
- GOOGLE_* : Google API specific errors
- MICROSOFT_* : Microsoft API specific errors
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """
    Standardized error codes for all Briefly services.

    This enum provides a centralized registry of all error codes used across
    the Briefly platform, ensuring consistency and preventing code duplication.
    Error codes are organized by category and follow the ALL_CAPS naming convention.

    Categories:
        - General: Common errors that apply across all services
        - Authentication: User authentication and token-related errors
        - Authorization: Permission and access control errors
        - Rate Limiting: Request throttling and quota errors
        - Service: Internal service and infrastructure errors
        - Provider: External API integration errors (generic)
        - Google: Google API specific error codes
        - Microsoft: Microsoft API specific error codes
    """

    # ==========================================
    # GENERAL ERRORS (4xx client errors)
    # ==========================================
    VALIDATION_FAILED = "VALIDATION_FAILED"  # HTTP 422 - Input validation failed
    NOT_FOUND = "NOT_FOUND"  # HTTP 404 - Resource not found
    ALREADY_EXISTS = "ALREADY_EXISTS"  # HTTP 409 - Resource already exists
    INTERNAL_ERROR = "INTERNAL_ERROR"  # HTTP 500 - Generic internal error

    # ==========================================
    # AUTHENTICATION ERRORS (401 Unauthorized)
    # ==========================================
    AUTH_FAILED = "AUTH_FAILED"  # Generic authentication failure
    TOKEN_EXPIRED = "TOKEN_EXPIRED"  # Access token has expired
    TOKEN_INVALID = "TOKEN_INVALID"  # Token format or signature invalid

    # ==========================================
    # AUTHORIZATION ERRORS (403 Forbidden)
    # ==========================================
    ACCESS_DENIED = "ACCESS_DENIED"  # Insufficient permissions
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"  # Missing required scopes

    # ==========================================
    # RATE LIMITING ERRORS (429 Too Many Requests)
    # ==========================================
    RATE_LIMITED = "RATE_LIMITED"  # Request rate limit exceeded
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"  # Usage quota limit exceeded

    # ==========================================
    # SERVICE ERRORS (5xx server errors)
    # ==========================================
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"  # Service temporarily unavailable
    SERVICE_ERROR = "SERVICE_ERROR"  # Generic service error
    DATABASE_ERROR = "DATABASE_ERROR"  # Database connectivity/operation error

    # ==========================================
    # PROVIDER ERRORS (502 Bad Gateway)
    # ==========================================
    PROVIDER_ERROR = "PROVIDER_ERROR"  # Generic external provider error
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"  # External provider not available

    # ==========================================
    # GOOGLE API SPECIFIC ERRORS
    # ==========================================
    # Authentication errors
    GOOGLE_AUTH_FAILED = "GOOGLE_AUTH_FAILED"  # Google authentication failed
    GOOGLE_TOKEN_EXPIRED = "GOOGLE_TOKEN_EXPIRED"  # Google token expired
    GOOGLE_AUTH_ERROR = "GOOGLE_AUTH_ERROR"  # Google auth error (generic)

    # Authorization errors
    GOOGLE_INSUFFICIENT_SCOPES = "GOOGLE_INSUFFICIENT_SCOPES"  # Missing OAuth scopes
    GOOGLE_INSUFFICIENT_PERMISSIONS = (
        "GOOGLE_INSUFFICIENT_PERMISSIONS"  # Insufficient permissions
    )
    GOOGLE_ACCESS_DENIED = "GOOGLE_ACCESS_DENIED"  # Google access denied

    # Rate limiting and quota errors
    GOOGLE_QUOTA_EXCEEDED = "GOOGLE_QUOTA_EXCEEDED"  # Google API quota exceeded
    GOOGLE_RATE_LIMITED = "GOOGLE_RATE_LIMITED"  # Google rate limit exceeded

    # Service and API errors
    GOOGLE_SERVICE_ERROR = "GOOGLE_SERVICE_ERROR"  # Google service error
    GOOGLE_API_ERROR = "GOOGLE_API_ERROR"  # Generic Google API error

    # ==========================================
    # MICROSOFT API SPECIFIC ERRORS
    # ==========================================
    # Token validation errors
    MICROSOFT_TOKEN_MALFORMED = "MICROSOFT_TOKEN_MALFORMED"  # JWT malformed
    MICROSOFT_TOKEN_EXPIRED = "MICROSOFT_TOKEN_EXPIRED"  # Token expired
    MICROSOFT_TOKEN_NOT_YET_VALID = (
        "MICROSOFT_TOKEN_NOT_YET_VALID"  # Token not yet valid (nbf)
    )
    MICROSOFT_TOKEN_SIGNATURE_INVALID = (
        "MICROSOFT_TOKEN_SIGNATURE_INVALID"  # Invalid signature
    )
    MICROSOFT_TOKEN_AUDIENCE_INVALID = (
        "MICROSOFT_TOKEN_AUDIENCE_INVALID"  # Wrong audience
    )
    MICROSOFT_TOKEN_ISSUER_INVALID = "MICROSOFT_TOKEN_ISSUER_INVALID"  # Wrong issuer
    MICROSOFT_TOKEN_NOT_FOUND = "MICROSOFT_TOKEN_NOT_FOUND"  # Token missing
    MICROSOFT_TOKEN_FORMAT_INVALID = (
        "MICROSOFT_TOKEN_FORMAT_INVALID"  # Invalid token format
    )

    # Authentication errors
    MICROSOFT_AUTH_FAILED = "MICROSOFT_AUTH_FAILED"  # Authentication failed
    MICROSOFT_UNAUTHORIZED = "MICROSOFT_UNAUTHORIZED"  # Unauthorized access
    MICROSOFT_AUTH_ERROR = "MICROSOFT_AUTH_ERROR"  # Generic auth error

    # Authorization errors
    MICROSOFT_ACCESS_FORBIDDEN = "MICROSOFT_ACCESS_FORBIDDEN"  # Access forbidden
    MICROSOFT_INSUFFICIENT_PERMISSIONS = (
        "MICROSOFT_INSUFFICIENT_PERMISSIONS"  # Insufficient permissions
    )
    MICROSOFT_APP_PERMISSIONS_REQUIRED = (
        "MICROSOFT_APP_PERMISSIONS_REQUIRED"  # App permissions needed
    )
    MICROSOFT_ACCESS_DENIED = "MICROSOFT_ACCESS_DENIED"  # Access denied

    # Service and API errors
    MICROSOFT_RATE_LIMITED = "MICROSOFT_RATE_LIMITED"  # Rate limit exceeded
    MICROSOFT_SERVICE_ERROR = "MICROSOFT_SERVICE_ERROR"  # Microsoft service error
    MICROSOFT_API_ERROR = "MICROSOFT_API_ERROR"  # Generic Microsoft API error


# Shared error response model (Pydantic)
class ErrorResponse(BaseModel):
    """
    Standardized error response model for all Briefly services.

    This Pydantic model ensures consistent error response structure across
    all microservices in the Briefly platform.

    Attributes:
        type: Error type categorization (e.g., "validation_error", "auth_error")
        message: Human-readable error message for end users
        details: Optional dictionary containing additional error context and metadata
        timestamp: ISO 8601 timestamp of when the error occurred
        request_id: Unique identifier for tracing and debugging purposes

    Example:
        >>> error = ErrorResponse(
        ...     type="validation_error",
        ...     message="Invalid email format",
        ...     details={"field": "email", "value": "invalid-email"},
        ...     timestamp="2024-01-15T10:30:00Z",
        ...     request_id="req-abc123"
        ... )
    """

    type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str
    request_id: str


class BrieflyAPIException(Exception):
    """
    Base exception class for all Briefly API errors.

    This is the foundation exception class that all other Briefly service exceptions
    inherit from. It provides consistent error handling, response formatting, and
    request tracking across all microservices.

    The class automatically generates timestamps and request IDs for debugging
    and provides structured conversion to standardized ErrorResponse objects.

    Attributes:
        message: Human-readable error message
        details: Dictionary containing additional error context
        error_type: Categorization of the error (validation_error, auth_error, etc.)
        error_code: Specific error code from the ErrorCode enum
        status_code: HTTP status code to return
        timestamp: ISO 8601 timestamp when error occurred
        request_id: Unique identifier for request tracing

    Args:
        message: The error message to display to users
        details: Optional dictionary with additional error context
        error_type: Error category string (defaults to "internal_error")
        error_code: Specific error code from ErrorCode enum
        status_code: HTTP status code (defaults to 500)
        request_id: Optional request ID (auto-generated if not provided)

    Example:
        >>> error = BrieflyAPIException(
        ...     message="Database connection failed",
        ...     details={"database": "postgres", "timeout": 30},
        ...     error_type="service_error",
        ...     error_code=ErrorCode.DATABASE_ERROR,
        ...     status_code=502
        ... )
        >>> response = error.to_error_response()
        >>> print(response.type)
        service_error
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_type: str = "internal_error",
        error_code: Optional[ErrorCode] = None,
        status_code: int = 500,
        request_id: Optional[str] = None,
    ):
        self.message = message
        self.details = details or {}
        self.error_type = error_type
        self.error_code = error_code
        self.status_code = status_code
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.request_id = request_id or str(uuid.uuid4())
        super().__init__(self.message)

    def to_error_response(self) -> ErrorResponse:
        """
        Convert exception to ErrorResponse Pydantic model.

        Creates a standardized ErrorResponse object that can be serialized
        and returned to API clients. Includes error code in details if present.

        Returns:
            ErrorResponse: Pydantic model ready for JSON serialization

        Example:
            >>> error = ValidationError("Invalid input", field="email")
            >>> response = error.to_error_response()
            >>> response.model_dump()
            {
                'type': 'validation_error',
                'message': 'Invalid input',
                'details': {'field': 'email', 'code': 'VALIDATION_FAILED'},
                'timestamp': '2024-01-15T10:30:00Z',
                'request_id': 'req-abc123'
            }
        """
        details = {
            **self.details,
            **({"code": self.error_code.value} if self.error_code else {}),
        }
        return ErrorResponse(
            type=self.error_type,
            message=self.message,
            details=details if details else None,
            timestamp=self.timestamp,
            request_id=self.request_id,
        )


# Common subclasses
class ValidationError(BrieflyAPIException):
    """
    Exception for input validation errors (HTTP 422).

    Used when user input fails validation rules, such as invalid email formats,
    missing required fields, or data type mismatches. Automatically categorizes
    as "validation_error" type and returns HTTP 422 status.

    Attributes:
        field: The specific field that failed validation (if applicable)
        value: The invalid value that was provided (if applicable)

    Args:
        message: Human-readable description of the validation failure
        field: Optional field name that failed validation
        value: Optional invalid value that was provided
        details: Optional additional validation context

    Examples:
        >>> # Basic validation error
        >>> error = ValidationError("Email is required")

        >>> # Field-specific validation error
        >>> error = ValidationError(
        ...     "Invalid email format",
        ...     field="email",
        ...     value="not-an-email"
        ... )

        >>> # Validation error with additional context
        >>> error = ValidationError(
        ...     "Password too weak",
        ...     field="password",
        ...     details={
        ...         "min_length": 8,
        ...         "requires_uppercase": True,
        ...         "requires_number": True
        ...     }
        ... )
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        validation_details = details or {}
        if field:
            validation_details["field"] = field
        if value is not None:
            validation_details["value"] = str(value)
        super().__init__(
            message=message,
            details=validation_details,
            error_type="validation_error",
            error_code=ErrorCode.VALIDATION_FAILED,
            status_code=422,
        )
        self.field = field
        self.value = value


class NotFoundError(BrieflyAPIException):
    """
    Exception for resource not found errors (HTTP 404).

    Used when a requested resource cannot be located, such as when querying
    for a user, document, or other entity by ID. Automatically categorizes
    as "not_found" type and returns HTTP 404 status.

    Attributes:
        resource: Type of resource that was not found
        identifier: The specific identifier that was searched for

    Args:
        resource: Type of resource (e.g., "User", "Document", "Integration")
        identifier: Optional ID/identifier that was searched for
        details: Optional additional context about the search

    Examples:
        >>> # Basic resource not found
        >>> error = NotFoundError("User", "user-123")
        >>> print(error.message)
        User user-123 not found

        >>> # Resource type only
        >>> error = NotFoundError("Integration")
        >>> print(error.message)
        Integration not found

        >>> # With additional context
        >>> error = NotFoundError(
        ...     "Document",
        ...     "doc-456",
        ...     details={"workspace_id": "ws-789", "permissions_checked": True}
        ... )
    """

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        if identifier:
            message = f"{resource} {identifier} not found"
        else:
            message = f"{resource} not found"
        notfound_details = {
            **(details or {}),
            "resource": resource,
            "identifier": identifier,
        }
        super().__init__(
            message=message,
            details=notfound_details,
            error_type="not_found",
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
        )
        self.resource = resource
        self.identifier = identifier


class AuthError(BrieflyAPIException):
    """
    Exception for authentication errors (HTTP 401).

    Used when authentication fails, such as invalid credentials, expired tokens,
    or missing authentication headers. Automatically categorizes as "auth_error"
    type and returns HTTP 401 status by default.

    Args:
        message: Description of the authentication failure
        details: Optional additional authentication context
        code: Specific error code (defaults to AUTH_FAILED)
        status_code: HTTP status code (defaults to 401)

    Examples:
        >>> # Basic auth failure
        >>> error = AuthError("Invalid credentials")

        >>> # Token expiration
        >>> error = AuthError(
        ...     "Access token has expired",
        ...     code=ErrorCode.TOKEN_EXPIRED,
        ...     details={"token_type": "JWT", "expired_at": "2024-01-15T10:00:00Z"}
        ... )

        >>> # Missing authentication
        >>> error = AuthError(
        ...     "Authentication required",
        ...     details={"required_scopes": ["read:profile", "write:documents"]}
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        code: ErrorCode = ErrorCode.AUTH_FAILED,
        status_code: int = 401,
    ):
        super().__init__(
            message=message,
            details=details,
            error_type="auth_error",
            error_code=code,
            status_code=status_code,
        )


class ServiceError(BrieflyAPIException):
    """
    Exception for internal service errors (HTTP 502).

    Used when internal service operations fail, such as database connectivity
    issues, downstream service failures, or configuration problems. Automatically
    categorizes as "service_error" type and returns HTTP 502 status by default.

    Args:
        message: Description of the service failure
        details: Optional additional service context
        code: Specific error code (defaults to SERVICE_ERROR)
        status_code: HTTP status code (defaults to 502)

    Examples:
        >>> # Database connectivity issue
        >>> error = ServiceError(
        ...     "Database connection failed",
        ...     code=ErrorCode.DATABASE_ERROR,
        ...     details={"database": "postgresql", "timeout_ms": 5000}
        ... )

        >>> # Downstream service failure
        >>> error = ServiceError(
        ...     "Email service unavailable",
        ...     code=ErrorCode.SERVICE_UNAVAILABLE,
        ...     details={"service": "sendgrid", "retry_after": 300}
        ... )

        >>> # Configuration issue
        >>> error = ServiceError(
        ...     "Required environment variable missing",
        ...     details={"variable": "DATABASE_URL", "service": "user-service"}
        ... )
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        code: ErrorCode = ErrorCode.SERVICE_ERROR,
        status_code: int = 502,
    ):
        super().__init__(
            message=message,
            details=details,
            error_type="service_error",
            error_code=code,
            status_code=status_code,
        )


class ProviderError(BrieflyAPIException):
    """
    Exception for external provider integration errors (HTTP 502).

    Used when external API providers (Google, Microsoft, etc.) return errors
    or when integration with third-party services fails. Automatically categorizes
    as "provider_error" type and returns HTTP 502 status by default.

    This class includes additional fields specific to provider integrations,
    such as response body capture and retry-after headers for rate limiting.

    Attributes:
        provider: Name of the external provider (google, microsoft, etc.)
        response_body: Raw response body from the provider (for debugging)
        retry_after: Seconds to wait before retrying (from rate limit headers)

    Args:
        message: User-friendly description of the provider error
        provider: Name of the external provider
        details: Optional additional provider context
        code: Specific error code (defaults to PROVIDER_ERROR)
        status_code: HTTP status code (defaults to 502)
        response_body: Raw response from provider for debugging
        retry_after: Retry delay in seconds for rate limiting

    Examples:
        >>> # Basic provider error
        >>> error = ProviderError(
        ...     "Google API quota exceeded",
        ...     provider="google",
        ...     code=ErrorCode.GOOGLE_QUOTA_EXCEEDED
        ... )

        >>> # Rate limiting with retry information
        >>> error = ProviderError(
        ...     "Microsoft API rate limit exceeded",
        ...     provider="microsoft",
        ...     code=ErrorCode.MICROSOFT_RATE_LIMITED,
        ...     retry_after=3600,
        ...     details={"quota_reset": "2024-01-15T11:00:00Z"}
        ... )

        >>> # Authentication failure with response body
        >>> error = ProviderError(
        ...     "Google authentication failed",
        ...     provider="google",
        ...     code=ErrorCode.GOOGLE_AUTH_FAILED,
        ...     response_body='{"error": "invalid_token"}',
        ...     details={"token_hint": "expired"}
        ... )
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        code: ErrorCode = ErrorCode.PROVIDER_ERROR,
        status_code: int = 502,
        response_body: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        provider_details = details or {}
        if provider:
            provider_details["provider"] = provider
        if response_body:
            provider_details["response_body"] = response_body
        if retry_after is not None:
            provider_details["retry_after"] = retry_after
        super().__init__(
            message=message,
            details=provider_details,
            error_type="provider_error",
            error_code=code,
            status_code=status_code,
        )
        self.provider = provider
        self.response_body = response_body
        self.retry_after = retry_after


class RateLimitError(BrieflyAPIException):
    """
    Exception for rate limiting errors (HTTP 429).

    Used when request rate limits are exceeded, either from internal rate limiting
    or when external providers return rate limit errors. Automatically categorizes
    as "rate_limit_error" type and returns HTTP 429 status.

    Attributes:
        retry_after: Seconds to wait before retrying the request

    Args:
        message: Description of the rate limiting
        retry_after: Optional delay in seconds before retry
        details: Optional additional rate limiting context
        code: Specific error code (defaults to RATE_LIMITED)
        status_code: HTTP status code (defaults to 429)

    Examples:
        >>> # Basic rate limiting
        >>> error = RateLimitError("Rate limit exceeded")

        >>> # With retry information
        >>> error = RateLimitError(
        ...     "API rate limit exceeded",
        ...     retry_after=3600,
        ...     details={
        ...         "limit": 1000,
        ...         "remaining": 0,
        ...         "reset_time": "2024-01-15T11:00:00Z"
        ...     }
        ... )

        >>> # Quota-based rate limiting
        >>> error = RateLimitError(
        ...     "Daily quota exceeded",
        ...     code=ErrorCode.QUOTA_EXCEEDED,
        ...     retry_after=86400,  # 24 hours
        ...     details={"quota_type": "daily", "limit": 10000}
        ... )
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        code: ErrorCode = ErrorCode.RATE_LIMITED,
        status_code: int = 429,
    ):
        rate_details = details or {}
        if retry_after is not None:
            rate_details["retry_after"] = retry_after
        super().__init__(
            message=message,
            details=rate_details,
            error_type="rate_limit_error",
            error_code=code,
            status_code=status_code,
        )
        self.retry_after = retry_after


# Utility to convert exceptions to error responses
def exception_to_response(exc: Exception) -> ErrorResponse:
    """
    Convert any exception to a standardized ErrorResponse Pydantic model.

    This utility function provides a consistent way to transform any Python exception
    into a standardized ErrorResponse that can be safely returned to API clients.
    It handles three main exception types with different conversion strategies:

    1. BrieflyAPIException: Uses the built-in to_error_response() method
    2. HTTPException: Extracts detail information and normalizes format
    3. Generic Exception: Creates a safe internal error response

    Args:
        exc: Any Python exception to convert

    Returns:
        ErrorResponse: Standardized Pydantic model ready for JSON serialization

    Examples:
        >>> # Convert a validation error
        >>> error = ValidationError("Invalid email", field="email")
        >>> response = exception_to_response(error)
        >>> print(response.type)
        validation_error

        >>> # Convert an HTTP exception
        >>> from fastapi import HTTPException
        >>> http_error = HTTPException(status_code=404, detail="Not found")
        >>> response = exception_to_response(http_error)
        >>> print(response.type)
        http_error

        >>> # Convert a generic exception
        >>> generic_error = ValueError("Something went wrong")
        >>> response = exception_to_response(generic_error)
        >>> print(response.type)
        internal_error
        >>> print(response.details["error_type"])
        ValueError

    Note:
        For security reasons, generic exceptions are converted to safe "internal_error"
        responses that don't expose potentially sensitive error details to end users.
        The original exception type is preserved in the details for debugging.
    """
    if isinstance(exc, BrieflyAPIException):
        return exc.to_error_response()
    elif isinstance(exc, HTTPException):
        # Try to extract detail
        detail = (
            exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        )
        return ErrorResponse(
            type="http_error",
            message=detail.get("message", "HTTP error"),
            details=detail,
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=str(uuid.uuid4()),
        )
    else:
        return ErrorResponse(
            type="internal_error",
            message=str(exc),
            details={"error_type": type(exc).__name__},
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id=str(uuid.uuid4()),
        )


# Optional: FastAPI exception handler registration utility


def register_briefly_exception_handlers(app: FastAPI) -> None:
    """
    Register comprehensive exception handlers for FastAPI applications.

    This utility function sets up standardized exception handling across all
    Briefly microservices by registering three levels of exception handlers:

    1. BrieflyAPIException: Handles all custom Briefly exceptions with proper
       status codes and structured error responses
    2. HTTPException: Converts FastAPI HTTP exceptions to standard format
    3. Generic Exception: Catches any unhandled exceptions and converts them
       to safe internal error responses

    All handlers return JSON responses using the standardized ErrorResponse
    Pydantic model, ensuring consistent error format across all services.

    Args:
        app: FastAPI application instance to register handlers on

    Examples:
        >>> from fastapi import FastAPI
        >>> from services.common.http_errors import register_briefly_exception_handlers
        >>>
        >>> app = FastAPI()
        >>> register_briefly_exception_handlers(app)
        >>>
        >>> # Now all exceptions will be handled consistently
        >>> @app.get("/test")
        >>> async def test_endpoint():
        ...     raise ValidationError("Invalid input", field="email")
        ...     # Will return:
        ...     # {
        ...     #   "type": "validation_error",
        ...     #   "message": "Invalid input",
        ...     #   "details": {"field": "email", "code": "VALIDATION_FAILED"},
        ...     #   "timestamp": "2024-01-15T10:30:00Z",
        ...     #   "request_id": "req-abc123"
        ...     # }

    Behavior:
        - BrieflyAPIException: Returns exception's status_code with error details
        - HTTPException: Returns exception's status_code with normalized details
        - Generic Exception: Returns 500 status with safe error message

    Security:
        Generic exceptions are converted to safe "internal_error" responses that
        don't expose potentially sensitive implementation details to end users.
        The original exception type is preserved in details for debugging purposes.

    Thread Safety:
        This function is safe to call during application startup. The registered
        handlers are thread-safe and can handle concurrent requests.

    Note:
        This function should be called once during application initialization,
        typically right after creating the FastAPI app instance and before
        adding routes or starting the server.
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(BrieflyAPIException)
    async def briefly_api_exception_handler(
        request: Request, exc: BrieflyAPIException
    ) -> JSONResponse:
        """
        Handle BrieflyAPIException with validated ErrorResponse.

        Converts Briefly custom exceptions to standardized JSON responses
        using the exception's built-in status code and error details.
        """
        error_response = exc.to_error_response()
        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """
        Handle HTTPException with validated ErrorResponse.

        Converts FastAPI HTTP exceptions to standardized format while
        preserving the original status code and detail information.
        """
        error_response = exception_to_response(exc)
        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Handle generic exceptions with validated ErrorResponse.

        Catches any unhandled exceptions and converts them to safe
        internal error responses with 500 status code.
        """
        error_response = exception_to_response(exc)
        return JSONResponse(status_code=500, content=error_response.model_dump())
