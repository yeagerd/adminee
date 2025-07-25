"""
Shipments Service - FastAPI Application

Provides package shipment tracking, label management, and carrier integration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.shipments.routers import api_router
from services.shipments.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="Briefly Shipments Service",
    version="0.1.0",
    description="Package shipment tracking microservice for Briefly.",
)

# CORS (allow all for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(api_router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"status": "healthy", "service": "shipments", "version": "0.1.0"}
