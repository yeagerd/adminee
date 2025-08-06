"""
Package management endpoints for the shipments service
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from common.pagination import PaginationConfig
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from services.common.logging_config import get_logger
from services.shipments.auth import get_current_user
from services.shipments.database import get_async_session_dep
from services.shipments.event_service import EventService
from services.shipments.models import Package, utc_now
from services.shipments.schemas import (
    PackageCreate,
    PackageOut,
    PackageUpdate,
)
from services.shipments.schemas.pagination import (
    CursorValidationError,
    PackageListResponse,
)
from services.shipments.service_auth import service_permission_required
from services.shipments.settings import get_settings
from services.shipments.utils import (
    normalize_tracking_number,
    validate_tracking_number_format,
)
from services.shipments.utils.pagination import ShipmentsCursorPagination

logger = get_logger(__name__)

router = APIRouter()


# Data collection schemas
class DataCollectionRequest(BaseModel):
    """Request schema for collecting user-corrected shipment data"""

    email_message_id: str = Field(..., description="Original email message ID")
    original_email_data: Dict[str, Any] = Field(
        ..., description="Original email content"
    )
    auto_detected_data: Dict[str, Any] = Field(
        ..., description="Auto-detected shipment data"
    )
    user_corrected_data: Dict[str, Any] = Field(
        ..., description="User-corrected shipment data"
    )
    detection_confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Original detection confidence"
    )
    correction_reason: Optional[str] = Field(
        None, description="Reason for user correction"
    )
    consent_given: bool = Field(
        ..., description="Whether user has given consent for data collection"
    )


class DataCollectionResponse(BaseModel):
    """Response schema for data collection"""

    success: bool = Field(..., description="Whether data collection was successful")
    collection_id: str = Field(
        ..., description="Unique identifier for this data collection entry"
    )
    timestamp: datetime = Field(..., description="When the data was collected")
    message: str = Field(..., description="Response message")


@router.get("", response_model=PackageListResponse)
@router.get("/", response_model=PackageListResponse)
async def list_packages(
    cursor: Optional[str] = None,
    limit: Optional[int] = None,
    direction: Optional[str] = "next",
    carrier: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> PackageListResponse:
    """
    List packages with cursor-based pagination.

    This endpoint uses cursor-based pagination instead of offset-based pagination
    for better performance and consistency with concurrent updates.
    """
    logger.info("Fetching packages with cursor pagination", user_id=current_user)

    # Basic rate limiting check (simple in-memory counter for demo)
    # In production, use Redis or a proper rate limiting service
    # TODO: Implement proper rate limiting with Redis
    # rate_limit_key = f"pagination_rate_limit:{current_user}"

    # Audit logging for pagination usage
    logger.info(
        "Pagination request",
        user_id=current_user,
        cursor_provided=bool(cursor),
        limit=limit,
        direction=direction,
        filters={"carrier": carrier, "status": status, "user_id": user_id},
    )

    # Initialize pagination configuration
    settings = get_settings()
    pagination_config = PaginationConfig(
        secret_key=settings.pagination_secret_key,
        token_expiry=settings.pagination_token_expiry,
        max_page_size=settings.pagination_max_page_size,
        default_page_size=settings.pagination_default_page_size,
    )

    pagination = ShipmentsCursorPagination(pagination_config)

    # Validate and sanitize limit
    limit = pagination.sanitize_limit(limit)

    # Input validation and sanitization
    if cursor and len(cursor) > 1000:  # Reasonable limit for cursor tokens
        raise HTTPException(
            status_code=400,
            detail=CursorValidationError(
                error="Cursor token too long",
                cursor_token=cursor[:50] + "...",  # Truncate for security
                reason="Token length exceeds maximum allowed",
            ).dict(),
        )

    if direction not in ["next", "prev"]:
        raise HTTPException(
            status_code=400,
            detail=CursorValidationError(
                error="Invalid pagination direction",
                cursor_token=cursor,
                reason="Direction must be 'next' or 'prev'",
            ).dict(),
        )

    # Decode cursor if provided
    cursor_info = None
    if cursor:
        cursor_info = pagination.decode_cursor(cursor)
        if not cursor_info:
            raise HTTPException(
                status_code=400,
                detail=CursorValidationError(
                    error="Invalid or expired cursor token",
                    cursor_token=cursor,
                    reason="Token validation failed",
                ).dict(),
            )

    # Build filters
    filters = {}
    if carrier:
        filters["carrier"] = carrier
    if status:
        filters["status"] = status
    if user_id:
        filters["user_id"] = user_id

    # Always filter by current user for security
    filters["user_id"] = current_user

    # Validate filters
    validated_filters = pagination.validate_shipments_filters(filters)

    # Build query with cursor pagination
    query = select(Package).where(Package.user_id == current_user)

    # Add cursor-based filtering if cursor is provided
    if cursor_info:
        if cursor_info.direction == "next":
            # For next page: (updated_at > last_updated) OR (updated_at = last_updated AND id > last_id)
            query = query.where(
                (Package.updated_at > cursor_info.last_timestamp)
                | (
                    (Package.updated_at == cursor_info.last_timestamp)
                    & (Package.id > cursor_info.last_id)
                )
            )
        else:
            # For previous page: (updated_at < last_updated) OR (updated_at = last_updated AND id < last_id)
            query = query.where(
                (Package.updated_at < cursor_info.last_timestamp)
                | (
                    (Package.updated_at == cursor_info.last_timestamp)
                    & (Package.id < cursor_info.last_id)
                )
            )

    # Add additional filters
    if validated_filters.get("carrier"):
        query = query.where(Package.carrier == validated_filters["carrier"])
    if validated_filters.get("status"):
        query = query.where(Package.status == validated_filters["status"])

    # Add ordering
    if direction == "next":
        query = query.order_by(Package.updated_at.asc(), Package.id.asc())
    else:
        query = query.order_by(Package.updated_at.desc(), Package.id.desc())

    # Add limit (fetch one extra to determine if there are more pages)
    query = query.limit(limit + 1)

    # Execute query
    result = await session.execute(query)
    packages = result.scalars().all()

    # Determine if there are more pages
    has_next = len(packages) > limit
    has_prev = cursor is not None  # If we have a cursor, we can go back

    # Remove the extra item used for pagination detection
    if has_next:
        packages = packages[:-1]

    # Convert to PackageOut with events count
    package_out = []
    for pkg in packages:
        # Get events count for this package
        if pkg.id is None:
            events_count = 0
        else:
            events_count = await EventService.get_events_count(session, pkg.id)

        package_out.append(
            PackageOut(
                id=pkg.id,  # type: ignore[arg-type]
                user_id=pkg.user_id,
                tracking_number=pkg.tracking_number,
                carrier=pkg.carrier,
                status=pkg.status,
                estimated_delivery=pkg.estimated_delivery,
                actual_delivery=pkg.actual_delivery,
                recipient_name=pkg.recipient_name,
                shipper_name=pkg.shipper_name,
                package_description=pkg.package_description,
                order_number=pkg.order_number,
                tracking_link=pkg.tracking_link,
                updated_at=pkg.updated_at,
                events_count=events_count,
                labels=[],
            )
        )

    # Create cursor info for response
    current_cursor_info = None
    if packages:
        last_package = packages[-1]
        current_cursor_info = pagination.create_shipments_cursor_info(
            last_id=str(last_package.id),
            last_updated=last_package.updated_at,
            filters=validated_filters,
            direction=direction,
            limit=limit,
        )

    # Convert PackageOut objects to dictionaries for the response
    package_dicts = [pkg.model_dump() for pkg in package_out]

    # Create pagination response
    response = pagination.create_shipments_pagination_response(
        packages=package_dicts,
        cursor_info=current_cursor_info,
        has_next=has_next,
        has_prev=has_prev,
    )

    logger.info(
        "Returning packages with cursor pagination",
        user_id=current_user,
        count=len(package_out),
        has_next=has_next,
        has_prev=has_prev,
    )

    return PackageListResponse(**response)


@router.post("", response_model=PackageOut)
@router.post("/", response_model=PackageOut)
async def add_package(
    pkg: PackageCreate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> PackageOut:
    # Normalize tracking number
    normalized_tracking = normalize_tracking_number(pkg.tracking_number, pkg.carrier)

    # Validate tracking number format
    if not validate_tracking_number_format(normalized_tracking, pkg.carrier):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tracking number format for carrier '{pkg.carrier}'",
        )

    # Check for existing package with same tracking number and carrier
    existing_query = select(Package).where(
        Package.user_id == current_user,
        Package.tracking_number == normalized_tracking,
        Package.carrier == pkg.carrier,
    )  # type: ignore
    existing_result = await session.execute(existing_query)
    existing_package = existing_result.scalar_one_or_none()

    if existing_package:
        raise HTTPException(
            status_code=409,
            detail=f"Package with tracking number '{normalized_tracking}' and carrier '{pkg.carrier}' already exists",
        )

    # Create package data with authenticated user's ID and normalized tracking number
    package_data = pkg.model_dump()
    package_data["user_id"] = current_user
    package_data["tracking_number"] = normalized_tracking

    db_pkg = Package(**package_data)  # type: ignore
    session.add(db_pkg)
    await session.commit()
    await session.refresh(db_pkg)

    # Extract all values before creating the tracking event
    package_id = db_pkg.id
    package_status = db_pkg.status
    user_id = db_pkg.user_id
    tracking_number = db_pkg.tracking_number
    carrier = db_pkg.carrier
    estimated_delivery = db_pkg.estimated_delivery
    actual_delivery = db_pkg.actual_delivery
    recipient_name = db_pkg.recipient_name
    shipper_name = db_pkg.shipper_name
    package_description = db_pkg.package_description
    order_number = db_pkg.order_number
    tracking_link = db_pkg.tracking_link
    updated_at = db_pkg.updated_at

    # Create initial tracking event
    if package_id is not None:
        await EventService.create_initial_event(
            session=session,
            package_id=package_id,
            status=package_status.value,
            email_message_id=pkg.email_message_id,
        )

    # Get events count
    if package_id is not None:
        events_count = await EventService.get_events_count(session, package_id)
    else:
        events_count = 0

    return PackageOut(
        id=package_id,  # type: ignore
        user_id=user_id,
        tracking_number=tracking_number,
        carrier=carrier,
        status=package_status,
        estimated_delivery=estimated_delivery,
        actual_delivery=actual_delivery,
        recipient_name=recipient_name,
        shipper_name=shipper_name,
        package_description=package_description,
        order_number=order_number,
        tracking_link=tracking_link,
        updated_at=updated_at,
        events_count=events_count,
        labels=[],  # TODO: Query for real labels
    )


@router.get("/{id}", response_model=PackageOut)
async def get_package(
    id: UUID,  # Changed from int to UUID
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> PackageOut:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Get events count
    if package.id is not None:
        events_count = await EventService.get_events_count(session, package.id)
    else:
        events_count = 0

    return PackageOut(
        id=package.id,  # type: ignore
        user_id=package.user_id,
        tracking_number=package.tracking_number,
        carrier=package.carrier,
        status=package.status,
        estimated_delivery=package.estimated_delivery,
        actual_delivery=package.actual_delivery,
        recipient_name=package.recipient_name,
        shipper_name=package.shipper_name,
        package_description=package.package_description,
        order_number=package.order_number,
        tracking_link=package.tracking_link,
        updated_at=package.updated_at,
        events_count=events_count,
        labels=[],  # TODO: Query for real labels
    )


@router.put("/{id}", response_model=PackageOut)
async def update_package(
    id: UUID,  # Changed from int to UUID
    pkg: PackageUpdate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> PackageOut:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Update package fields
    update_data = pkg.dict(exclude_unset=True)

    # Handle tracking number normalization if it's being updated
    if "tracking_number" in update_data:
        normalized_tracking = normalize_tracking_number(
            update_data["tracking_number"], package.carrier
        )

        # Validate tracking number format
        if not validate_tracking_number_format(normalized_tracking, package.carrier):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tracking number format for carrier '{package.carrier}'",
            )

        # Check for existing package with same tracking number and carrier (excluding current package)
        existing_query = select(Package).where(
            Package.user_id == current_user,
            Package.tracking_number == normalized_tracking,
            Package.carrier == package.carrier,
            Package.id != id,
        )  # type: ignore
        existing_result = await session.execute(existing_query)
        existing_package = existing_result.scalar_one_or_none()

        if existing_package:
            raise HTTPException(
                status_code=409,
                detail=f"Package with tracking number '{normalized_tracking}' and carrier '{package.carrier}' already exists",
            )

        update_data["tracking_number"] = normalized_tracking

    for field, value in update_data.items():
        setattr(package, field, value)  # type: ignore

    package.updated_at = utc_now()
    await session.commit()
    await session.refresh(package)

    # Get events count
    if package.id is not None:
        events_count = await EventService.get_events_count(session, package.id)
    else:
        events_count = 0

    return PackageOut(
        id=package.id,  # type: ignore
        user_id=package.user_id,
        tracking_number=package.tracking_number,
        carrier=package.carrier,
        status=package.status,
        estimated_delivery=package.estimated_delivery,
        actual_delivery=package.actual_delivery,
        recipient_name=package.recipient_name,
        shipper_name=package.shipper_name,
        package_description=package.package_description,
        order_number=package.order_number,
        tracking_link=package.tracking_link,
        updated_at=package.updated_at,
        events_count=events_count,
        labels=[],  # TODO: Query for real labels
    )


@router.delete("/{id}")
async def delete_package(
    id: UUID,  # Changed from int to UUID
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # Delete all tracking events for this package first
    if package.id is not None:
        await EventService.delete_package_events(session, package.id)

    # Delete the package
    await session.delete(package)
    await session.commit()

    return {"message": "Package deleted successfully"}


@router.post("/{id}/refresh")
async def refresh_package(
    id: UUID,  # Changed from int to UUID
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # TODO: Implement actual tracking refresh logic
    # For now, just update the timestamp
    package.updated_at = utc_now()
    await session.commit()

    return {"message": "Package refresh initiated successfully"}


@router.post("/{id}/labels")
async def add_label_to_package(
    id: UUID,  # Changed from int to UUID
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # TODO: Implement actual label addition logic
    return {"message": "Label added to package successfully"}


@router.delete("/{id}/labels/{label_id}")
async def remove_label_from_package(
    id: UUID,  # Changed from int to UUID
    label_id: UUID,  # Changed from int to UUID
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)  # type: ignore
    result = await session.execute(query)
    package = result.scalar_one_or_none()

    if not package:
        raise HTTPException(
            status_code=404, detail="Package not found or access denied"
        )

    # TODO: Implement actual label removal logic
    return {"message": "Label removed from package successfully"}


# Data collection endpoints
@router.post("/collect-data", response_model=DataCollectionResponse)
async def collect_shipment_data(
    request: DataCollectionRequest,
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["collect_data"])),
) -> DataCollectionResponse:
    """
    Collect user-corrected shipment data for service improvements

    This endpoint stores:
    - Original email content
    - Auto-detected shipment information
    - User corrections and improvements
    - Detection confidence scores

    This data is used to improve the accuracy of future shipment detection.
    """
    try:
        logger.info(
            "Collecting shipment data for improvements",
            authenticated_user=current_user,
            email_id=request.email_message_id,
        )
        # Validate user consent
        if not request.consent_given:
            logger.warning(
                "Data collection attempted without user consent",
                user_id=current_user,
                email_id=request.email_message_id,
            )
            raise HTTPException(
                status_code=403, detail="Data collection requires explicit user consent"
            )

        # Generate collection ID
        collection_id = f"collection_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{current_user[:8]}"

        # Log the data collection (in production, this would be stored in a database)
        logger.info(
            "Collecting shipment data for improvements",
            collection_id=collection_id,
            user_id=current_user,
            email_id=request.email_message_id,
            confidence=request.detection_confidence,
            has_corrections=bool(request.correction_reason),
        )

        # TODO: Store data in database for training improvements
        # For now, we'll just log the data structure
        training_data = {
            "collection_id": collection_id,
            "user_id": current_user,
            "email_message_id": request.email_message_id,
            "original_email_data": request.original_email_data,
            "auto_detected_data": request.auto_detected_data,
            "user_corrected_data": request.user_corrected_data,
            "detection_confidence": request.detection_confidence,
            "correction_reason": request.correction_reason,
            "consent_given": request.consent_given,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

        # In a real implementation, this would be stored in a database
        # For now, we'll just log it for demonstration
        logger.info("Training data structure", training_data=training_data)

        return DataCollectionResponse(
            success=True,
            collection_id=collection_id,
            timestamp=datetime.now(timezone.utc),
            message="Shipment data collected successfully for service improvements",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error collecting shipment data",
            error=str(e),
            user_id=current_user,
            email_id=request.email_message_id,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to collect shipment data",
                "details": str(e),
                "error_code": "COLLECTION_ERROR",
            },
        )


@router.get("/collection-stats")
async def get_collection_stats(
    current_user: str = Depends(get_current_user),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> Dict[str, Any]:
    """
    Get statistics about data collection (for admin/monitoring purposes)
    """
    try:
        logger.info("Getting data collection stats", user_id=current_user)
        # TODO: Implement actual statistics from database
        # For now, return placeholder stats
        stats = {
            "total_collections": 0,
            "collections_today": 0,
            "average_confidence": 0.0,
            "correction_rate": 0.0,
            "top_correction_reasons": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        return stats

    except Exception as e:
        logger.error("Error getting collection stats", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve collection statistics"
        )


# Package-specific tracking events endpoints have been moved to tracking_events.py
# and are now routed through the router configuration in __init__.py
