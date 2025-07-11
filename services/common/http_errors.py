"""
Shared HTTP error classes and utilities for all Briefly services.

Provides:
- Base exception class for API errors
- Common subclasses (Validation, Auth, NotFound, Service, Provider, RateLimit)
- Shared error response model
- Utility to convert exceptions to error responses
- (Optional) FastAPI exception handler registration
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException
from pydantic import BaseModel


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
        error_code: Optional[str] = None,
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
            **({"code": self.error_code} if self.error_code else {}),
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
            error_code="VALIDATION_FAILED",
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
            error_code="NOT_FOUND",
            status_code=404,
        )
        self.resource = resource
        self.identifier = identifier


class AuthError(BrieflyAPIException):
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        code: str = "AUTH_FAILED",
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
        code: str = "SERVICE_ERROR",
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
        code: str = "PROVIDER_ERROR",
        status_code: int = 502,
    ):
        provider_details = details or {}
        if provider:
            provider_details["provider"] = provider
        super().__init__(
            message=message,
            details=provider_details,
            error_type="provider_error",
            error_code=code,
            status_code=status_code,
        )
        self.provider = provider


class RateLimitError(BrieflyAPIException):
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        code: str = "RATE_LIMITED",
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
