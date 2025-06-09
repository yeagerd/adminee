"""
Custom exceptions for the Office Service.

Defines application-specific exceptions for better error handling
and standardized error responses.
"""

from typing import Any, Dict, Optional

from models import Provider


class OfficeServiceError(Exception):
    """Base exception for all Office Service errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional error details
            error_code: Application-specific error code
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code


class ProviderAPIError(OfficeServiceError):
    """
    Exception raised when external provider APIs fail.

    This exception is used to wrap errors from Google, Microsoft, and other
    external service APIs to provide consistent error handling.
    """

    def __init__(
        self,
        message: str,
        provider: Provider,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        retry_after: Optional[int] = None,
    ):
        """
        Initialize the provider API error.

        Args:
            message: Human-readable error message
            provider: The provider that caused the error
            status_code: HTTP status code from the provider API
            response_body: Raw response body from the provider API
            details: Additional error details
            retry_after: Seconds to wait before retrying (for rate limiting)
        """
        super().__init__(message, details)
        self.provider = provider
        self.status_code = status_code
        self.response_body = response_body
        self.retry_after = retry_after


class TokenError(OfficeServiceError):
    """Exception raised when token operations fail."""

    def __init__(
        self,
        message: str,
        provider: Optional[Provider] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the token error.

        Args:
            message: Human-readable error message
            provider: The provider associated with the token
            user_id: The user ID associated with the token
            details: Additional error details
        """
        super().__init__(message, details)
        self.provider = provider
        self.user_id = user_id


class ValidationError(OfficeServiceError):
    """Exception raised when request validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the validation error.

        Args:
            message: Human-readable error message
            field: The field that failed validation
            value: The invalid value
            details: Additional error details
        """
        super().__init__(message, details)
        self.field = field
        self.value = value


class CacheError(OfficeServiceError):
    """Exception raised when cache operations fail."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the cache error.

        Args:
            message: Human-readable error message
            operation: The cache operation that failed (get, set, delete)
            key: The cache key involved
            details: Additional error details
        """
        super().__init__(message, details)
        self.operation = operation
        self.key = key


class DatabaseError(OfficeServiceError):
    """Exception raised when database operations fail."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the database error.

        Args:
            message: Human-readable error message
            operation: The database operation that failed
            table: The table involved in the operation
            details: Additional error details
        """
        super().__init__(message, details)
        self.operation = operation
        self.table = table


class RateLimitError(OfficeServiceError):
    """Exception raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str,
        provider: Optional[Provider] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the rate limit error.

        Args:
            message: Human-readable error message
            provider: The provider that rate limited the request
            retry_after: Seconds to wait before retrying
            details: Additional error details
        """
        super().__init__(message, details)
        self.provider = provider
        self.retry_after = retry_after
