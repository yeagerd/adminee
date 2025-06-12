import logging
import uuid
from datetime import datetime, timezone

import httpx
from services.office_service.api.calendar import router as calendar_router
from services.office_service.api.email import router as email_router
from services.office_service.api.files import router as files_router
from services.office_service.api.health import router as health_router
from services.office_service.core.config import settings
from services.office_service.core.exceptions import (
    OfficeServiceError,
    ProviderAPIError,
    RateLimitError,
    TokenError,
    ValidationError,
)
from services.office_service.core.logging_config import setup_logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from services.office_service.schemas import ApiError

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="A backend microservice responsible for all external API interactions with Google and Microsoft services",
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)


# Global Exception Handlers
@app.exception_handler(ProviderAPIError)
async def provider_api_error_handler(
    request: Request, exc: ProviderAPIError
) -> JSONResponse:
    """
    Handle ProviderAPIError exceptions.

    Logs the full error and returns a standardized 500-level ApiError response.
    """
    request_id = str(uuid.uuid4())

    logger.error(
        "Provider API error occurred",
        extra={
            "request_id": request_id,
            "provider": exc.provider.value if exc.provider else None,
            "status_code": exc.status_code,
            "error_message": exc.message,
            "response_body": exc.response_body,
            "details": exc.details,
            "url": str(request.url),
            "method": request.method,
        },
        exc_info=True,
    )

    # Determine appropriate HTTP status code
    status_code = 502  # Bad Gateway for provider errors
    if exc.status_code:
        if exc.status_code == 429:
            status_code = 429  # Too Many Requests
        elif exc.status_code >= 400 and exc.status_code < 500:
            status_code = 400  # Bad Request for client errors

    error_response = ApiError(
        type="provider_error",
        message=f"External service error: {exc.message}",
        details=exc.details,
        provider=exc.provider,
        retry_after=exc.retry_after,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(),
    )


@app.exception_handler(TokenError)
async def token_error_handler(request: Request, exc: TokenError) -> JSONResponse:
    """Handle TokenError exceptions."""
    request_id = str(uuid.uuid4())

    logger.error(
        "Token error occurred",
        extra={
            "request_id": request_id,
            "provider": exc.provider.value if exc.provider else None,
            "user_id": exc.user_id,
            "error_message": exc.message,
            "details": exc.details,
            "url": str(request.url),
            "method": request.method,
        },
        exc_info=True,
    )

    error_response = ApiError(
        type="auth_error",
        message=f"Authentication error: {exc.message}",
        details=exc.details,
        provider=exc.provider,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=401,
        content=error_response.model_dump(),
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(
    request: Request, exc: RateLimitError
) -> JSONResponse:
    """Handle RateLimitError exceptions."""
    request_id = str(uuid.uuid4())

    logger.warning(
        "Rate limit exceeded",
        extra={
            "request_id": request_id,
            "provider": exc.provider.value if exc.provider else None,
            "error_message": exc.message,
            "retry_after": exc.retry_after,
            "details": exc.details,
            "url": str(request.url),
            "method": request.method,
        },
    )

    error_response = ApiError(
        type="rate_limit_error",
        message=f"Rate limit exceeded: {exc.message}",
        details=exc.details,
        provider=exc.provider,
        retry_after=exc.retry_after,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=429,
        content=error_response.model_dump(),
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {},
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    """Handle ValidationError exceptions."""
    request_id = str(uuid.uuid4())

    logger.warning(
        "Validation error occurred",
        extra={
            "request_id": request_id,
            "field": exc.field,
            "value": exc.value,
            "error_message": exc.message,
            "details": exc.details,
            "url": str(request.url),
            "method": request.method,
        },
    )

    error_response = ApiError(
        type="validation_error",
        message=f"Validation error: {exc.message}",
        details=exc.details,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=400,
        content=error_response.model_dump(),
    )


@app.exception_handler(OfficeServiceError)
async def office_service_error_handler(
    request: Request, exc: OfficeServiceError
) -> JSONResponse:
    """Handle generic OfficeServiceError exceptions."""
    request_id = str(uuid.uuid4())

    logger.error(
        "Office service error occurred",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "error_message": exc.message,
            "details": exc.details,
            "url": str(request.url),
            "method": request.method,
        },
        exc_info=True,
    )

    error_response = ApiError(
        type="service_error",
        message=f"Service error: {exc.message}",
        details=exc.details,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(),
    )


@app.exception_handler(httpx.HTTPError)
async def httpx_error_handler(request: Request, exc: httpx.HTTPError) -> JSONResponse:
    """Handle httpx HTTP errors."""
    request_id = str(uuid.uuid4())

    logger.error(
        "HTTP client error occurred",
        extra={
            "request_id": request_id,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "url": str(request.url),
            "method": request.method,
        },
        exc_info=True,
    )

    error_response = ApiError(
        type="http_error",
        message="External service communication error",
        details={"error": str(exc)},
        request_id=request_id,
    )

    return JSONResponse(
        status_code=502,
        content=error_response.model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    request_id = str(uuid.uuid4())

    logger.error(
        "Unhandled exception occurred",
        extra={
            "request_id": request_id,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "url": str(request.url),
            "method": request.method,
        },
        exc_info=True,
    )

    error_response = ApiError(
        type="internal_error",
        message="An internal server error occurred",
        details={"error_type": type(exc).__name__} if settings.DEBUG else {},
        request_id=request_id,
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(),
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(
        "Office Service starting up",
        extra={
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
        },
    )


# Include routers
app.include_router(health_router)
app.include_router(email_router)
app.include_router(calendar_router)
app.include_router(files_router)


@app.get("/")
async def read_root():
    """Hello World root endpoint"""
    logger.info("Root endpoint accessed")
    return {"message": "Hello World", "service": "Office Service"}


@app.get("/ready")
async def ready_check():
    """
    Simple readiness check.
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
