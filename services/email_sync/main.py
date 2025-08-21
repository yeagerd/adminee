"""
Briefly Email Sync Service - FastAPI Application

Provides email synchronization and processing capabilities.
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

# Set up centralized logging - will be initialized in lifespan
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup event logic
    log_service_startup(
        "email-sync",
        version="0.1.0",
        environment="development",
    )
    yield
    # Shutdown event logic
    log_service_shutdown("email-sync")


app = FastAPI(
    title="Briefly Email Sync Service",
    version="0.1.0",
    description="Email synchronization and processing microservice for Briefly",
    contact={
        "name": "Briefly Team",
        "email": "support@briefly.ai",
    },
    license_info={
        "name": "Private",
    },
    openapi_tags=[
        {"name": "sync", "description": "Email synchronization operations"},
        {"name": "processing", "description": "Email processing and analysis"},
        {"name": "health", "description": "Health check and service status endpoints"},
    ],
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


@app.get("/")
def root() -> dict:
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the Briefly Email Sync Service"}


@app.get("/health")
def health() -> dict:
    logger.info("Health check endpoint accessed")
    return {"status": "ok", "service": "email-sync", "version": "0.1.0"}


@app.get("/openapi.json")
def get_openapi_schema() -> dict:
    """Return the OpenAPI schema for this service."""
    return app.openapi()
