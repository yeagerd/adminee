"""
User Management Service - FastAPI Application

This is the main entry point for the User Management Service.
Provides user profile management, preferences, and OAuth integrations.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import connect_database, database, disconnect_database
from .exceptions import (
    AuditException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException,
    EncryptionException,
    IntegrationAlreadyExistsException,
    IntegrationException,
    IntegrationNotFoundException,
    InternalError,
    PreferencesNotFoundException,
    ServiceException,
    TokenExpiredException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserManagementException,
    UserNotFoundException,
    ValidationException,
    WebhookValidationException,
)
from .logging_config import setup_logging
from .middleware.sanitization import (
    InputSanitizationMiddleware,
    XSSProtectionMiddleware,
)
from .routers import (
    integrations_router,
    internal_router,
    preferences_router,
    provider_router,
    users_router,
    webhooks_router,
)
from .settings import settings

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for database connections
    and other resources.
    """
    # Startup
    logger.info("Starting User Management Service")
    try:
        await connect_database()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down User Management Service")
    try:
        await disconnect_database()
        logger.info("Database disconnected successfully")
    except Exception as e:
        logger.error(f"Error during database disconnect: {e}")


# Create FastAPI application with enhanced configuration
app = FastAPI(
    title="User Management Service",
    description="Manages user profiles, preferences, and OAuth integrations for the Briefly platform",
    version="0.1.0",
    contact={
        "name": "Briefly Team",
        "email": "support@briefly.ai",
    },
    license_info={
        "name": "Private",
    },
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add security middleware
app.add_middleware(XSSProtectionMiddleware)
app.add_middleware(
    InputSanitizationMiddleware,
    enabled=True,
    strict_mode=settings.debug,  # Use strict mode in development
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(users_router)
app.include_router(preferences_router)
app.include_router(integrations_router)
app.include_router(provider_router)
app.include_router(webhooks_router)
app.include_router(internal_router)


# Specific exception handlers
@app.exception_handler(UserNotFoundException)
async def user_not_found_handler(request: Request, exc: UserNotFoundException):
    """Handle user not found exceptions."""
    logger.info(
        f"User not found: {exc.message}",
        extra={
            "user_id": exc.user_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "request_headers": dict(request.headers),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=exc.to_error_response(),
    )


@app.exception_handler(PreferencesNotFoundException)
async def preferences_not_found_handler(
    request: Request, exc: PreferencesNotFoundException
):
    """Handle preferences not found exceptions."""
    logger.info(f"Preferences not found: {exc.message}", extra={"user_id": exc.user_id})
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=exc.to_error_response(),
    )


@app.exception_handler(IntegrationNotFoundException)
async def integration_not_found_handler(
    request: Request, exc: IntegrationNotFoundException
):
    """Handle integration not found exceptions."""
    logger.info(
        f"Integration not found: {exc.message}",
        extra={"user_id": exc.user_id, "provider": exc.provider},
    )
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=exc.to_error_response(),
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    """Handle validation exceptions."""
    logger.info(
        f"Validation error: {exc.message}",
        extra={
            "field": exc.field,
            "value": exc.value,
            "reason": exc.reason,
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "query_params": dict(request.query_params),
        },
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=exc.to_error_response(),
    )


@app.exception_handler(AuthenticationException)
async def authentication_exception_handler(
    request: Request, exc: AuthenticationException
):
    """Handle authentication exceptions."""
    logger.warning(
        f"Authentication failed: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None,
            "authorization_header_present": "authorization" in request.headers,
        },
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=exc.to_error_response(),
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(AuthorizationException)
async def authorization_exception_handler(
    request: Request, exc: AuthorizationException
):
    """Handle authorization exceptions."""
    logger.warning(
        f"Authorization failed: {exc.message}",
        extra={"resource": exc.resource, "action": exc.action},
    )
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=exc.to_error_response(),
    )


@app.exception_handler(WebhookValidationException)
async def webhook_validation_exception_handler(
    request: Request, exc: WebhookValidationException
):
    """Handle webhook validation exceptions."""
    logger.warning(
        f"Webhook validation failed: {exc.message}",
        extra={"provider": exc.provider, "reason": exc.reason},
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.to_error_response(),
    )


@app.exception_handler(UserAlreadyExistsException)
async def user_already_exists_handler(
    request: Request, exc: UserAlreadyExistsException
):
    """Handle user already exists exceptions."""
    logger.info(f"User already exists: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=exc.to_error_response(),
    )


@app.exception_handler(IntegrationAlreadyExistsException)
async def integration_already_exists_handler(
    request: Request, exc: IntegrationAlreadyExistsException
):
    """Handle integration already exists exceptions."""
    logger.info(f"Integration already exists: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=exc.to_error_response(),
    )


@app.exception_handler(TokenNotFoundException)
async def token_not_found_handler(request: Request, exc: TokenNotFoundException):
    """Handle token not found exceptions."""
    logger.info(f"Token not found: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=exc.to_error_response(),
    )


@app.exception_handler(TokenExpiredException)
async def token_expired_handler(request: Request, exc: TokenExpiredException):
    """Handle token expired exceptions."""
    logger.info(f"Token expired: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=exc.to_error_response(),
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(EncryptionException)
async def encryption_exception_handler(request: Request, exc: EncryptionException):
    """Handle encryption exceptions."""
    logger.error(
        f"Encryption error: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "error_type": exc.error_type,
            "details": exc.details,
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=exc.to_error_response(),
    )


@app.exception_handler(DatabaseException)
async def database_exception_handler(request: Request, exc: DatabaseException):
    """Handle database exceptions."""
    logger.error(
        f"Database error: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "error_type": exc.error_type,
            "details": exc.details,
            "operation": exc.details.get("operation", "unknown"),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=exc.to_error_response(),
    )


@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException):
    """Handle service exceptions."""
    logger.error(f"Service error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=exc.to_error_response(),
    )


@app.exception_handler(AuditException)
async def audit_exception_handler(request: Request, exc: AuditException):
    """Handle audit exceptions."""
    logger.error(f"Audit error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=exc.to_error_response(),
    )


@app.exception_handler(IntegrationException)
async def integration_exception_handler(request: Request, exc: IntegrationException):
    """Handle integration exceptions."""
    logger.warning(f"Integration error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.to_error_response(),
    )


@app.exception_handler(InternalError)
async def internal_error_handler(request: Request, exc: InternalError):
    """Handle internal errors."""
    logger.error(f"Internal error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=exc.to_error_response(),
    )


@app.exception_handler(UserManagementException)
async def user_management_exception_handler(
    request: Request, exc: UserManagementException
):
    """Handle general user management exceptions."""
    logger.error(
        f"User management error: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.error_code,
            "error_type": exc.error_type,
            "details": exc.details,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None,
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=exc.to_error_response(),
    )


# Global exception handler (fallback)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.

    Logs the error and returns a generic error response to avoid
    exposing internal details in production.
    """
    import uuid
    from datetime import datetime, timezone

    request_id = str(uuid.uuid4())

    logger.error(
        "Unhandled exception occurred",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "request_id": request_id,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "type": "internal_error",
            "message": "An unexpected error occurred. Please try again later.",
            "details": {
                "error_type": type(exc).__name__,
                "path": request.url.path,
                "method": request.method,
                "code": "INTERNAL_SERVER_ERROR",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
        },
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and database connectivity information.
    Performs basic database connectivity test.
    """
    health_status = {
        "status": "healthy",
        "service": "user-management",
        "version": "0.1.0",
        "environment": settings.environment,
        "database": {"status": "unknown"},
    }

    # Check database connectivity
    try:
        if database.is_connected:
            # Perform a simple query to test database connectivity
            await database.execute("SELECT 1")
            health_status["database"]["status"] = "healthy"
        else:
            health_status["database"]["status"] = "disconnected"
            health_status["status"] = "unhealthy"
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        health_status["database"]["status"] = "error"
        health_status["database"]["error"] = str(e)
        health_status["status"] = "unhealthy"

    return health_status


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )
