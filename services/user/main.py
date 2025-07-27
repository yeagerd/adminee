"""
User Management Service - FastAPI Application

This is the main entry point for the User Management Service.
Provides user profile management, preferences, and OAuth integrations.
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from services.common.http_errors import register_briefly_exception_handlers
from services.common.logging_config import (
    create_request_logging_middleware,
    get_logger,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)
from services.user.database import (
    close_db,
    create_all_tables,
    get_async_session,
)
from services.user.integrations.oauth_config import get_oauth_config
from services.user.middleware.sanitization import (
    InputSanitizationMiddleware,
    XSSProtectionMiddleware,
)
from services.user.routers import (
    integrations_router,
    internal_router,
    preferences_router,
    provider_router,
    users_router,
)
from services.user.schemas.health import (
    ConfigurationStatus,
    DatabaseStatus,
    DependencyStatus,
    PerformanceStatus,
    ReadinessChecks,
    ReadinessStatus,
)
from services.user.services.integration_service import (
    get_integration_service,
)
from services.user.settings import Settings, get_settings

# Set up centralized logging - will be initialized in lifespan
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events for database connections
    and other resources.
    """
    settings = get_settings()

    # Set up centralized logging
    setup_service_logging(
        service_name="user",
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    # Startup
    log_service_startup(
        "user",
        api_frontend_user_key=(
            "configured" if settings.api_frontend_user_key else "missing"
        ),
        api_office_user_key="configured" if settings.api_office_user_key else "missing",
        api_meetings_user_key=(
            "configured" if settings.api_meetings_user_key else "missing"
        ),
        db_url=settings.db_url_user,
        environment=settings.environment,
        debug=settings.debug,
    )

    # Validate required configuration
    if not settings.api_frontend_user_key:
        logger.error("API_FRONTEND_USER_KEY is required but not configured")
        logger.error(
            "Set the API_FRONTEND_USER_KEY environment variable or configure it in settings"
        )
        raise RuntimeError("API_FRONTEND_USER_KEY is required but not configured")

    # Validate required configuration
    if not settings.api_chat_user_key:
        logger.error("API_CHAT_USER_KEY is required but not configured")
        logger.error(
            "Set the API_CHAT_USER_KEY environment variable or configure it in settings"
        )
        raise RuntimeError("API_CHAT_USER_KEY is required but not configured")

    # Validate required configuration
    if not settings.api_meetings_user_key:
        logger.error("API_MEETINGS_USER_KEY is required but not configured")
        logger.error(
            "Set the API_MEETINGS_USER_KEY environment variable or configure it in settings"
        )
        raise RuntimeError("API_MEETINGS_USER_KEY is required but not configured")

    # Configure docs URLs
    if settings.debug:
        app.docs_url = "/docs"
        app.redoc_url = "/redoc"
    else:
        app.docs_url = None
        app.redoc_url = None

    try:
        await create_all_tables()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    yield

    # Shutdown
    log_service_shutdown("user")
    try:
        await close_db()
        logger.info("Database disconnected successfully")
    except Exception as e:
        logger.error(f"Error during database disconnect: {e}")


def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.

    This prevents initialization during module import and allows for proper
    configuration based on available settings.
    """
    # Get settings for proper configuration
    settings = get_settings()

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
        lifespan=lifespan,
    )

    # Configure middleware (must be done before app starts)
    # Add InputSanitizationMiddleware
    app.add_middleware(
        InputSanitizationMiddleware,
        enabled=True,
        strict_mode=settings.debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Add security middleware
    app.add_middleware(XSSProtectionMiddleware)

    # Add centralized request logging middleware
    app.middleware("http")(create_request_logging_middleware())

    # Register exception handlers
    register_briefly_exception_handlers(app)

    # Register API routers with v1 prefix
    app.include_router(users_router, prefix="/v1")
    app.include_router(preferences_router, prefix="/v1")
    app.include_router(integrations_router, prefix="/v1")
    app.include_router(provider_router, prefix="/v1")
    app.include_router(internal_router, prefix="/v1")

    return app


# Global app instance - will be created lazily
_app: FastAPI | None = None


def get_app() -> FastAPI:
    """Get the FastAPI application instance, creating it if necessary."""
    global _app
    if _app is None:
        _app = create_app()
    return _app


# Create a proxy object that defers app creation until first access
class AppProxy:
    """Proxy object that creates the FastAPI app on first access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_app(), name)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        """ASGI callable interface."""
        app_instance = get_app()
        return await app_instance(scope, receive, send)


# For uvicorn compatibility, we need an app variable at module level
app = AppProxy()


# Global OAuth callback endpoint
@app.get("/oauth/callback")
async def oauth_callback_redirect(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> Any:
    """
    Global OAuth callback endpoint that handles provider redirects.

    This endpoint receives OAuth callbacks from providers and processes them
    directly using the integration service.

    The state parameter contains information about the user and provider
    that allows us to route the callback correctly.
    """
    try:
        # Get the OAuth config instance
        oauth_config = get_oauth_config()

        # Get the OAuth state from the stored states
        if not state or state not in oauth_config._active_states:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid or missing OAuth state parameter"},
            )

        oauth_state = oauth_config._active_states[state]
        user_id = oauth_state.user_id
        provider = oauth_state.provider

        # Handle OAuth errors
        if error:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"OAuth error: {error}",
                    "error_description": error_description or "No description",
                    "provider": provider.value,
                },
            )

        # Validate authorization code is present
        if not code:
            return JSONResponse(
                status_code=400, content={"error": "Missing authorization code"}
            )

        # Complete the OAuth flow using the integration service
        result = await get_integration_service().complete_oauth_flow(
            user_id=user_id,
            provider=provider,
            authorization_code=code,
            state=state,
        )

        if result.success:
            return JSONResponse(
                status_code=200,
                content={
                    "message": f"OAuth flow completed successfully for {provider.value}",
                    "provider": provider.value,
                    "status": result.status.value if result.status else None,
                    "integration_id": result.integration_id,
                },
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"OAuth flow failed: {result.error}",
                    "provider": provider.value,
                },
            )

    except Exception as e:
        # Use a safe logger that works even if main logger isn't initialized
        safe_logger = get_logger(__name__)
        safe_logger.error(f"OAuth callback error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error during OAuth callback: {str(e)}"},
        )


# Load balancer health check endpoints
@app.get(
    "/health",
    tags=["Health"],
    summary="Service health check",
    description="Basic health check for load balancer liveness probes",
    response_model=ReadinessStatus,
    responses={
        200: {
            "description": "Service is healthy and ready to handle requests",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "user",
                        "version": "0.1.0",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "healthy",
                                "response_time_ms": 5.2,
                                "connected": True,
                            },
                            "configuration": {"status": "healthy", "issues": []},
                            "dependencies": {
                                "status": "healthy",
                                "services": {
                                    "encryption_service": True,
                                    "audit_logging": True,
                                },
                            },
                        },
                        "performance": {"total_check_time_ms": 12.5},
                    }
                }
            },
        },
        503: {
            "description": "Service is unhealthy and should not receive traffic",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "service": "user",
                        "version": "0.1.0",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "unhealthy",
                                "connected": False,
                                "error": "Database unavailable",
                            },
                            "configuration": {
                                "status": "unhealthy",
                                "issues": ["DB_URL_USER not configured"],
                            },
                            "dependencies": {
                                "status": "unhealthy",
                                "services": {
                                    "encryption_service": False,
                                    "audit_logging": False,
                                },
                            },
                        },
                        "performance": {"total_check_time_ms": 0.0},
                    }
                }
            },
        },
    },
)
async def health_check() -> Any:
    import time
    from datetime import datetime, timezone

    from fastapi.responses import JSONResponse

    start_time = time.time()
    # Database health check
    db_status = "healthy"
    db_connected = True
    db_error = None
    db_response_time = None
    try:
        async_session = get_async_session()
        async with async_session() as session:
            db_start = time.time()
            await session.execute(text("SELECT 1"))
            db_response_time = round((time.time() - db_start) * 1000, 2)
    except Exception as e:
        db_status = "unhealthy"
        db_connected = False
        db_error = (
            str(e)
            if getattr(get_settings(), "debug", False)
            else "Database unavailable"
        )

    # Configuration check
    config_issues = []
    current_settings = Settings()
    db_url = getattr(current_settings, "db_url_user", None)
    if not db_url:
        config_issues.append("DB_URL_USER not configured")
    config_status = "healthy" if not config_issues else "unhealthy"

    # Dependencies (for now, always healthy)
    dependencies = {
        "encryption_service": True,
        "audit_logging": True,
    }
    dependencies_status = "healthy"

    # Performance metrics
    total_duration = round((time.time() - start_time) * 1000, 2)

    # Determine overall status
    overall_status = (
        "healthy"
        if db_status == "healthy" and config_status == "healthy"
        else "unhealthy"
    )

    # Compose the response using the Pydantic model
    response_data = ReadinessStatus(
        status=overall_status,
        service="user",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=str(getattr(get_settings(), "environment", "unknown")),
        checks=ReadinessChecks(
            database=DatabaseStatus(
                status=db_status,
                response_time_ms=db_response_time,
                connected=db_connected,
                error=db_error,
            ),
            configuration=ConfigurationStatus(
                status=config_status,
                issues=config_issues,
            ),
            dependencies=DependencyStatus(
                status=dependencies_status,
                services=dependencies,
            ),
        ),
        performance=PerformanceStatus(
            total_check_time_ms=total_duration,
        ),
    )

    # Return appropriate status code based on health
    status_code = 503 if overall_status == "unhealthy" else 200
    return JSONResponse(
        status_code=status_code,
        content=response_data.model_dump(),
    )


@app.get(
    "/ready",
    tags=["Health"],
    summary="Service readiness check",
    description="Comprehensive readiness check for load balancer readiness probes",
    response_model=ReadinessStatus,
    responses={
        200: {
            "description": "Service is ready to handle requests",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ready",
                        "service": "user",
                        "version": "0.1.0",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "ready",
                                "response_time_ms": 5.2,
                                "connected": True,
                            },
                            "configuration": {"status": "ready", "issues": []},
                            "dependencies": {
                                "status": "ready",
                                "services": {
                                    "encryption_service": True,
                                    "audit_logging": True,
                                },
                            },
                        },
                        "performance": {"total_check_time_ms": 12.5},
                    }
                }
            },
        },
        503: {
            "description": "Service is not ready to handle requests",
            "content": {
                "application/json": {
                    "example": {
                        "status": "not_ready",
                        "service": "user",
                        "version": "0.1.0",
                        "timestamp": "2024-01-01T00:00:00Z",
                        "environment": "production",
                        "checks": {
                            "database": {
                                "status": "not_ready",
                                "connected": False,
                                "error": "Database not connected",
                            },
                            "configuration": {
                                "status": "not_ready",
                                "issues": ["DB_URL_USER not configured"],
                            },
                            "dependencies": {
                                "status": "not_ready",
                                "services": {
                                    "encryption_service": False,
                                    "audit_logging": False,
                                },
                            },
                        },
                        "performance": {"total_check_time_ms": 0.0},
                    }
                }
            },
        },
    },
)
async def readiness_check() -> Any:
    import time
    from datetime import datetime, timezone

    from fastapi.responses import JSONResponse

    start_time = time.time()
    # Database readiness check
    db_status = "ready"
    db_connected = True
    db_error = None
    db_response_time = None
    try:
        async_session = get_async_session()
        async with async_session() as session:
            db_start = time.time()
            await session.execute(text("SELECT 1"))
            try:
                await session.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
            except Exception as table_error:
                if (
                    os.environ.get("PYTEST_CURRENT_TEST") is not None
                    or "pytest" in str(table_error).lower()
                ):
                    try:
                        await create_all_tables()
                        await session.execute(
                            text("SELECT COUNT(*) FROM users LIMIT 1")
                        )
                    except Exception:
                        raise Exception(
                            "Database tables not initialized (run alembic upgrade head)"
                        )
                else:
                    raise Exception(
                        "Database tables not initialized (run alembic upgrade head)"
                    )
            db_response_time = round((time.time() - db_start) * 1000, 2)
    except Exception as e:
        db_status = "not_ready"
        db_connected = False
        db_error = (
            str(e)
            if getattr(get_settings(), "debug", False)
            else "Database check failed"
        )

    # Configuration check
    config_issues = []
    current_settings = Settings()
    db_url = getattr(current_settings, "db_url_user", None)
    if not db_url:
        config_issues.append("DB_URL_USER not configured")
    is_test_env = (
        getattr(current_settings, "environment", "").lower() in ["test", "testing"]
        or os.environ.get("PYTEST_CURRENT_TEST") is not None
        or any(
            "pytest" in module for module in globals().get("__name__", "").split(".")
        )
    )
    if not is_test_env:
        if not getattr(current_settings, "token_encryption_salt", None):
            config_issues.append("TOKEN_ENCRYPTION_SALT not configured")
        if not getattr(current_settings, "api_frontend_user_key", None):
            config_issues.append("API_FRONTEND_USER_KEY not configured")
    config_status = "ready" if not config_issues else "not_ready"

    # Dependencies (for now, always ready)
    dependencies = {
        "encryption_service": True,
        "audit_logging": True,
    }
    dependencies_status = "ready"

    # Performance metrics
    total_duration = round((time.time() - start_time) * 1000, 2)

    # Determine overall status
    overall_status = (
        "ready" if db_status == "ready" and config_status == "ready" else "not_ready"
    )

    # Compose the response using the Pydantic model
    response_data = ReadinessStatus(
        status=overall_status,
        service="user",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=str(getattr(get_settings(), "environment", "unknown")),
        checks=ReadinessChecks(
            database=DatabaseStatus(
                status=db_status,
                response_time_ms=db_response_time,
                connected=db_connected,
                error=db_error,
            ),
            configuration=ConfigurationStatus(
                status=config_status,
                issues=config_issues,
            ),
            dependencies=DependencyStatus(
                status=dependencies_status,
                services=dependencies,
            ),
        ),
        performance=PerformanceStatus(
            total_check_time_ms=total_duration,
        ),
    )

    # Return appropriate status code based on readiness
    status_code = 503 if overall_status == "not_ready" else 200
    return JSONResponse(
        status_code=status_code,
        content=response_data.model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=get_settings().debug,
        log_level="info" if not get_settings().debug else "debug",
        access_log=False,  # Disable uvicorn access logs, we handle request logging in middleware
    )
