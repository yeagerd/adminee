from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict

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
from services.office.api.email import router as email_router
from services.office.api.files import router as files_router
from services.office.api.health import router as health_router
from services.office.core.settings import get_settings

# Set up centralized logging - will be initialized in lifespan

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup event logic
    settings = get_settings()

    # Set up centralized logging
    setup_service_logging(
        service_name="office-service",
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    log_service_startup(
        "office-service",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        user_management_service_url=settings.USER_MANAGEMENT_SERVICE_URL,
    )
    yield
    # Shutdown event logic
    log_service_shutdown("office-service")


app = FastAPI(
    title="Office Service",
    description="A backend microservice responsible for all external API interactions with Google and Microsoft services",
    version="0.1.0",
    debug=False,
    lifespan=lifespan,
)

# Add centralized request logging middleware
app.middleware("http")(create_request_logging_middleware())

register_briefly_exception_handlers(app)


# Include routers with v1 prefix
app.include_router(health_router, prefix="/v1")
app.include_router(email_router, prefix="/v1")
app.include_router(calendar_router, prefix="/v1")
app.include_router(files_router, prefix="/v1")


@app.get("/")
async def read_root() -> Dict[str, str]:
    """Hello World root endpoint"""
    logger.info("Root endpoint accessed")
    return {"message": "Hello World", "service": "Office Service"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Simple health check endpoint for load balancers and monitoring.
    This endpoint is used by the start-all-services.sh script.
    """
    return {
        "status": "ok",
        "service": "Office Service",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
async def ready_check() -> Dict[str, str]:
    """
    Simple readiness check.
    """
    return {
        "status": "ok",
        "service": "Office Service",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
