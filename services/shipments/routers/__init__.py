"""
API routers for the shipments service
"""

from fastapi import APIRouter

from services.shipments.routers import (
    carrier_configs,
    labels,
    packages,
    tracking_events,
)

# Create main shipments router
shipments_router = APIRouter()

# Include all sub-routers under /shipments
shipments_router.include_router(packages.router, prefix="/packages", tags=["Packages"])
shipments_router.include_router(labels.router, prefix="/labels", tags=["Labels"])
shipments_router.include_router(
    carrier_configs.router, prefix="/carriers", tags=["Carriers"]
)

# Create the main API router
api_router = APIRouter()

# Include the shipments router under /shipments
api_router.include_router(shipments_router, prefix="/shipments", tags=["Shipments"])

# Include tracking events router under events to match expected URL pattern
# This allows /api/v1/shipments/events/from-email to work
api_router.include_router(
    tracking_events.router, prefix="/shipments/events", tags=["Events"]
)
