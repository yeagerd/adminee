"""
API routers for the shipments service
"""

from fastapi import APIRouter

from services.shipments.routers import packages, labels, tracking_events, carrier_configs

api_router = APIRouter()
api_router.include_router(packages.router, prefix="/packages", tags=["Packages"])
api_router.include_router(labels.router, prefix="/labels", tags=["Labels"])
api_router.include_router(tracking_events.router, prefix="/tracking", tags=["Tracking"])
api_router.include_router(carrier_configs.router, prefix="/carriers", tags=["Carriers"])
