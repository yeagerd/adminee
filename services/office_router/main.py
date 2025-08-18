#!/usr/bin/env python3
"""
Office Router Service - Central routing service for office data distribution
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware

from services.common.logging_config import (
    setup_service_logging,
    create_request_logging_middleware,
    log_service_startup,
    log_service_shutdown
)
from services.common.http_errors import (
    register_briefly_exception_handlers,
    ValidationError,
    NotFoundError,
    AuthError,
    ServiceError
)
from services.office_router.pubsub_consumer import PubSubConsumer
from services.office_router.router import OfficeRouter
from services.office_router.settings import Settings

# Global service instances
router: Optional[OfficeRouter] = None
pubsub_consumer: Optional[PubSubConsumer] = None
settings: Optional[Settings] = None

async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key")
) -> str:
    """Verify API key for inter-service communication"""
    if not settings:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    if x_api_key not in [
        settings.api_frontend_office_router_key,
        settings.api_office_router_user_key,
        settings.api_office_router_office_key,
    ]:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global router, pubsub_consumer, settings

    # Startup
    logger.info("Starting Office Router Service...")

    # Initialize settings
    settings = Settings()

    # Setup logging
    setup_service_logging(
        service_name=settings.service_name,
        log_level=settings.log_level,
        log_format="json" if settings.log_level == "DEBUG" else "text",
    )

    # Initialize router
    router = OfficeRouter(settings)

    # Initialize and start pubsub consumer
    pubsub_consumer = PubSubConsumer(settings, router)
    await pubsub_consumer.start()

    log_service_startup(settings.service_name, version="1.0.0")
    logger.info("Office Router Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Office Router Service...")
    if pubsub_consumer:
        await pubsub_consumer.stop()
    log_service_shutdown(settings.service_name)
    logger.info("Office Router Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Office Router Service",
    description="Central routing service for office data distribution",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
app.middleware("http")(create_request_logging_middleware())

# Register exception handlers
register_briefly_exception_handlers(app)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "office-router", "version": "1.0.0"}


@app.get("/status")
async def service_status():
    """Service status endpoint"""
    if not router or not pubsub_consumer:
        raise HTTPException(status_code=503, detail="Service not ready")

    return {
        "router": {
            "status": "running",
            "downstream_services": router.get_downstream_services(),
        },
        "pubsub": {
            "status": "running" if pubsub_consumer.get_running_status() else "stopped",
            "subscriptions": pubsub_consumer.get_subscription_status(),
        },
    }


@app.post("/route/email")
async def route_email(
    email_data: dict,
    api_key: str = Depends(verify_api_key)
):
    """Route email data to downstream services"""
    if not router:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await router.route_email(email_data)
        return {"status": "routed", "result": result}
    except Exception as e:
        logger.error(f"Failed to route email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/route/calendar")
async def route_calendar(
    calendar_data: dict,
    api_key: str = Depends(verify_api_key)
):
    """Route calendar data to downstream services"""
    if not router:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await router.route_calendar(calendar_data)
        return {"status": "routed", "result": result}
    except Exception as e:
        logger.error(f"Failed to route calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/route/contact")
async def route_contact(
    contact_data: dict,
    api_key: str = Depends(verify_api_key)
):
    """Route contact data to downstream services"""
    if not router:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await router.route_contact(contact_data)
        return {"status": "routed", "result": result}
    except Exception as e:
        logger.error(f"Failed to route contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8006, reload=True, log_level="info")
