"""
Shipments Service - FastAPI Application

Provides package shipment tracking, label management, and carrier integration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.common.http_errors import register_briefly_exception_handlers
from services.common.logging_config import (
    create_request_logging_middleware,
    get_logger,
    log_service_shutdown,
    log_service_startup,
    setup_service_logging,
)
from services.shipments.routers import api_router
from services.shipments.settings import get_settings

# Set up centralized logging - will be initialized in lifespan
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup event logic
    settings = get_settings()

    # Set up centralized logging
    setup_service_logging(
        service_name="shipments",
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    log_service_startup(
        "shipments",
        version="0.1.0",
        environment=settings.environment,
        debug=settings.debug,
    )
    yield
    # Shutdown event logic
    log_service_shutdown("shipments")


app = FastAPI(
    title="Briefly Shipments Service",
    version="0.1.0",
    description="Package shipment tracking microservice for Briefly.",
    lifespan=lifespan,
)

# CORS (allow all for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())

# Register exception handlers
register_briefly_exception_handlers(app)

# Register routers with v1 prefix
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "shipments", "version": "0.1.0"}
