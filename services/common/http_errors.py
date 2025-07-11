"""
Shared HTTP error classes and utilities for all Briefly services.

Provides:
- Base exception class for API errors
- Common subclasses (Validation, Auth, NotFound, Service, Provider, RateLimit)
- Shared error response model
- Utility to convert exceptions to error responses
- (Optional) FastAPI exception handler registration

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

from fastapi import HTTPException
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Standardized error codes for all Briefly services."""
    
    # General errors
    VALIDATION_FAILED = "VALIDATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    
    # Authentication and authorization
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    ACCESS_DENIED = "ACCESS_DENIED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Rate limiting
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    
    # Service errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_ERROR = "SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # Provider errors (generic)
    PROVIDER_ERROR = "PROVIDER_ERROR"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    
    # Google-specific errors
    GOOGLE_AUTH_FAILED = "GOOGLE_AUTH_FAILED"
    GOOGLE_TOKEN_EXPIRED = "GOOGLE_TOKEN_EXPIRED"
    GOOGLE_INSUFFICIENT_SCOPES = "GOOGLE_INSUFFICIENT_SCOPES"
    GOOGLE_AUTH_ERROR = "GOOGLE_AUTH_ERROR"
    GOOGLE_INSUFFICIENT_PERMISSIONS = "GOOGLE_INSUFFICIENT_PERMISSIONS"
    GOOGLE_QUOTA_EXCEEDED = "GOOGLE_QUOTA_EXCEEDED"
    GOOGLE_ACCESS_DENIED = "GOOGLE_ACCESS_DENIED"
    GOOGLE_RATE_LIMITED = "GOOGLE_RATE_LIMITED"
    GOOGLE_SERVICE_ERROR = "GOOGLE_SERVICE_ERROR"
    GOOGLE_API_ERROR = "GOOGLE_API_ERROR"
    
    # Microsoft-specific errors
    MICROSOFT_TOKEN_MALFORMED = "MICROSOFT_TOKEN_MALFORMED"
    MICROSOFT_TOKEN_EXPIRED = "MICROSOFT_TOKEN_EXPIRED"
    MICROSOFT_TOKEN_NOT_YET_VALID = "MICROSOFT_TOKEN_NOT_YET_VALID"
    MICROSOFT_TOKEN_SIGNATURE_INVALID = "MICROSOFT_TOKEN_SIGNATURE_INVALID"
    MICROSOFT_TOKEN_AUDIENCE_INVALID = "MICROSOFT_TOKEN_AUDIENCE_INVALID"
    MICROSOFT_TOKEN_ISSUER_INVALID = "MICROSOFT_TOKEN_ISSUER_INVALID"
    MICROSOFT_AUTH_FAILED = "MICROSOFT_AUTH_FAILED"
    MICROSOFT_UNAUTHORIZED = "MICROSOFT_UNAUTHORIZED"
    MICROSOFT_TOKEN_NOT_FOUND = "MICROSOFT_TOKEN_NOT_FOUND"
    MICROSOFT_TOKEN_FORMAT_INVALID = "MICROSOFT_TOKEN_FORMAT_INVALID"
    MICROSOFT_AUTH_ERROR = "MICROSOFT_AUTH_ERROR"
    MICROSOFT_ACCESS_FORBIDDEN = "MICROSOFT_ACCESS_FORBIDDEN"
    MICROSOFT_INSUFFICIENT_PERMISSIONS = "MICROSOFT_INSUFFICIENT_PERMISSIONS"
    MICROSOFT_APP_PERMISSIONS_REQUIRED = "MICROSOFT_APP_PERMISSIONS_REQUIRED"
    MICROSOFT_ACCESS_DENIED = "MICROSOFT_ACCESS_DENIED"
    MICROSOFT_RATE_LIMITED = "MICROSOFT_RATE_LIMITED"
    MICROSOFT_SERVICE_ERROR = "MICROSOFT_SERVICE_ERROR"
    MICROSOFT_API_ERROR = "MICROSOFT_API_ERROR"


# Shared error response model (Pydantic)
class ErrorResponse(BaseModel):
    type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str
    request_id: str


class BrieflyAPIException(Exception):
    """Base exception for all Briefly API errors."""

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
        """Convert exception to ErrorResponse Pydantic model."""
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
    """Convert any exception to ErrorResponse Pydantic model."""
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
def register_briefly_exception_handlers(app):
    """
    Register exception handlers for FastAPI app with ErrorResponse model validation.
    
    Args:
        app: FastAPI application instance
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(BrieflyAPIException)
    async def briefly_api_exception_handler(request: Request, exc: BrieflyAPIException):
        """Handle BrieflyAPIException with validated ErrorResponse."""
        error_response = exc.to_error_response()
        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTPException with validated ErrorResponse."""
        error_response = exception_to_response(exc)
        return JSONResponse(status_code=exc.status_code, content=error_response.model_dump())

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handle generic exceptions with validated ErrorResponse."""
        error_response = exception_to_response(exc)
        return JSONResponse(status_code=500, content=error_response.model_dump())
