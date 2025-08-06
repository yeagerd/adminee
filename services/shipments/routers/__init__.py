"""
API routers for the shipments service
"""

from fastapi import APIRouter

from services.shipments.routers import (
    carrier_configs,
    events,
    labels,
    package_events,
    packages,
)

# Create main shipments router
shipments_router = APIRouter()

# Include all sub-routers under /shipments
shipments_router.include_router(packages.router, prefix="/packages", tags=["Packages"])
shipments_router.include_router(labels.router, prefix="/labels", tags=["Labels"])
shipments_router.include_router(
    carrier_configs.router, prefix="/carriers", tags=["Carriers"]
)

# Include package-specific tracking events router
# This allows /api/v1/shipments/packages/{id}/events to work
shipments_router.include_router(
    package_events.package_events_router, prefix="/packages", tags=["Package Events"]
)

# Include general email parsing and event management router
# This allows /api/v1/shipments/events/from-email to work
shipments_router.include_router(events.events_router, prefix="/events", tags=["Events"])

# Create the main API router
api_router = APIRouter()

# Include the shipments router under /shipments
api_router.include_router(shipments_router, prefix="/shipments", tags=["Shipments"])
