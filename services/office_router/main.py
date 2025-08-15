#!/usr/bin/env python3
"""
Office Router Service - Central routing service for office data distribution
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from contextlib import asynccontextmanager
from typing import Optional

from .router import OfficeRouter
from .settings import Settings
from .pubsub_consumer import PubSubConsumer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global service instances
router: Optional[OfficeRouter] = None
pubsub_consumer: Optional[PubSubConsumer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global router, pubsub_consumer
    
    # Startup
    logger.info("Starting Office Router Service...")
    
    # Initialize settings
    settings = Settings()
    
    # Initialize router
    router = OfficeRouter(settings)
    
    # Initialize and start pubsub consumer
    pubsub_consumer = PubSubConsumer(settings, router)
    await pubsub_consumer.start()
    
    logger.info("Office Router Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Office Router Service...")
    if pubsub_consumer:
        await pubsub_consumer.stop()
    logger.info("Office Router Service shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="Office Router Service",
    description="Central routing service for office data distribution",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "office-router",
        "version": "1.0.0"
    }

@app.get("/status")
async def service_status():
    """Service status endpoint"""
    if not router or not pubsub_consumer:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {
        "router": {
            "status": "running",
            "downstream_services": router.get_downstream_services()
        },
        "pubsub": {
            "status": "running" if pubsub_consumer.get_running_status() else "stopped",
            "subscriptions": pubsub_consumer.get_subscription_status()
        }
    }

@app.post("/route/email")
async def route_email(email_data: dict):
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
async def route_calendar(calendar_data: dict):
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
async def route_contact(contact_data: dict):
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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
