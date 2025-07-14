import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict

from fastapi import FastAPI

from services.common.http_errors import register_briefly_exception_handlers
from services.common.logging_config import (
    create_request_logging_middleware,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)
from services.office.api.calendar import router as calendar_router
from services.office.api.email import router as email_router
from services.office.api.files import router as files_router
from services.office.api.health import router as health_router
from services.office.core.settings import get_settings

# Set up centralized logging
settings = get_settings()
setup_service_logging(
    service_name="office-service",
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    # Startup event logic
    settings = get_settings()
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
    title=get_settings().APP_NAME,
    description="A backend microservice responsible for all external API interactions with Google and Microsoft services",
    version=get_settings().APP_VERSION,
    debug=get_settings().DEBUG,
    lifespan=lifespan,
)

# Add centralized request logging middleware
app.middleware("http")(create_request_logging_middleware())

register_briefly_exception_handlers(app)


# Include routers
app.include_router(health_router)
app.include_router(email_router)
app.include_router(calendar_router)
app.include_router(files_router)


@app.get("/")
async def read_root() -> Dict[str, str]:
    """Hello World root endpoint"""
    logger.info("Root endpoint accessed")
    return {"message": "Hello World", "service": "Office Service"}


@app.get("/ready")
async def ready_check() -> Dict[str, str]:
    """
    Simple readiness check.
    """
    return {
        "status": "ok",
        "service": get_settings().APP_NAME,
        "version": get_settings().APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
