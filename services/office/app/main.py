from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI

from services.common.http_errors import register_briefly_exception_handlers
from services.common.logging_config import (
    create_request_logging_middleware,
    get_logger,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)
from services.office.api.calendar import router as calendar_router
from services.office.api.contacts import router as contacts_router
from services.office.api.email import router as email_router
from services.office.api.files import router as files_router
from services.office.core.settings import get_settings

# Set up centralized logging - will be initialized in lifespan

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup event logic
    settings = get_settings()

    # Set up centralized logging
    setup_service_logging(
        service_name="office",
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    log_service_startup(
        "office",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        user_service_url=settings.USER_SERVICE_URL,
    )
    yield
    # Shutdown event logic
    log_service_shutdown("office")


app = FastAPI(
    title="Briefly Office Service",
    description="Backend microservice for Google and Microsoft integrations including email, calendar, files, and contacts",
    version="0.1.0",
    contact={
        "name": "Briefly Team",
        "email": "support@briefly.ai",
    },
    license_info={
        "name": "Private",
    },
    openapi_tags=[
        {
            "name": "email",
            "description": "Email operations including sending, receiving, and management",
        },
        {
            "name": "calendar",
            "description": "Calendar operations including events and availability",
        },
        {
            "name": "files",
            "description": "File operations including upload, download, and management",
        },
        {"name": "contacts", "description": "Contact management and operations"},
    ],
    debug=False,
    lifespan=lifespan,
)

# Add centralized request logging middleware
app.middleware("http")(create_request_logging_middleware())

register_briefly_exception_handlers(app)


# Include routers with v1 prefix
app.include_router(email_router, prefix="/v1")
app.include_router(calendar_router, prefix="/v1")
app.include_router(files_router, prefix="/v1")
app.include_router(contacts_router, prefix="/v1")


@app.get("/")
async def read_root() -> Dict[str, str]:
    """Hello World root endpoint"""
    logger.info("Root endpoint accessed")
    settings = get_settings()
    return {"message": "Hello World", "service": settings.APP_NAME}


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for load balancers and monitoring.
    Checks database connectivity and basic configuration.
    """
    import time
    from datetime import datetime, timezone

    start_time = time.time()

    # Database health check
    db_status = "ok"
    db_error = None
    db_response_time = None

    try:
        from sqlmodel import text

        from services.office.models import get_async_session_factory

        async_session_factory = get_async_session_factory()
        async with async_session_factory() as session:
            db_start = time.time()
            await session.execute(text("SELECT 1"))
            db_response_time = round((time.time() - db_start) * 1000, 2)
    except Exception as e:
        db_status = "error"
        db_error = str(e) if get_settings().DEBUG else "Database unavailable"

    # Configuration check
    config_issues = []
    if not get_settings().api_frontend_office_key:
        config_issues.append("API_FRONTEND_OFFICE_KEY not configured")
    if not get_settings().api_chat_office_key:
        config_issues.append("API_CHAT_OFFICE_KEY not configured")
    if not get_settings().USER_SERVICE_URL:
        config_issues.append("USER_SERVICE_URL not configured")

    config_status = "ok" if not config_issues else "error"

    # Determine overall status
    overall_status = "ok" if db_status == "ok" and config_status == "ok" else "error"

    # Calculate total response time
    total_duration = round((time.time() - start_time) * 1000, 2)

    settings = get_settings()
    return {
        "status": overall_status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": {
                "status": db_status,
                "response_time_ms": db_response_time,
                "error": db_error,
            },
            "configuration": {"status": config_status, "issues": config_issues},
        },
        "performance": {"total_check_time_ms": total_duration},
    }


@app.get("/ready")
async def ready_check() -> Dict[str, str]:
    """
    Simple readiness check.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
