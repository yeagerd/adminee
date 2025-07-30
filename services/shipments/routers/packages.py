from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from services.common.logging_config import get_logger
from services.shipments.auth import get_current_user
from services.shipments.database import get_async_session_dep
from services.shipments.models import Package
from services.shipments.schemas import (
    PackageCreate,
    PackageListResponse,
    PackageOut,
    PackageUpdate,
)
from services.shipments.service_auth import service_permission_required

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=PackageListResponse)
async def list_packages(
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> dict:
    logger.info("Fetching packages for user", user_id=current_user)
    result = await session.execute(select(Package).where(Package.user_id == current_user))
    packages = result.scalars().all()
    logger.info("Found packages for user", user_id=current_user, count=len(packages))
    # Convert to PackageOut (minimal fields for now)
    package_out = [
        PackageOut(
            id=pkg.id if pkg.id is not None else 0,
            user_id=str(pkg.user_id),
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
            events_count=0,
            labels=[],
        )
        for pkg in packages
    ]
    return {
        "data": package_out,
        "pagination": {"page": 1, "per_page": 100, "total": len(package_out)},
    }


@router.post("/", response_model=PackageOut)
async def add_package(
    pkg: PackageCreate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> PackageOut:
    # Create package data with authenticated user's ID
    package_data = pkg.dict()
    package_data["user_id"] = current_user

    db_pkg = Package(**package_data)
    session.add(db_pkg)
    await session.commit()
    await session.refresh(db_pkg)
    return PackageOut(
        id=db_pkg.id if db_pkg.id is not None else 0,
        user_id=str(db_pkg.user_id),
        tracking_number=db_pkg.tracking_number,
        carrier=db_pkg.carrier,
        status=db_pkg.status,
        estimated_delivery=db_pkg.estimated_delivery,
        actual_delivery=db_pkg.actual_delivery,
        recipient_name=db_pkg.recipient_name,
        shipper_name=db_pkg.shipper_name,
        package_description=db_pkg.package_description,
        order_number=db_pkg.order_number,
        tracking_link=db_pkg.tracking_link,
        updated_at=db_pkg.updated_at,
        events_count=0,  # TODO: Query for real count
        labels=[],  # TODO: Query for real labels
    )


@router.get("/{id}", response_model=PackageOut)
async def get_package(
    id: int,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["read_shipments"])),
) -> PackageOut:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)
    result = await session.execute(query)
    package = result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found or access denied")
    
    return PackageOut(
        id=package.id if package.id is not None else 0,
        user_id=str(package.user_id),
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
        events_count=0,  # TODO: Query for real count
        labels=[],  # TODO: Query for real labels
    )


@router.put("/{id}", response_model=PackageOut)
async def update_package(
    id: int,
    pkg: PackageUpdate,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> PackageOut:
    # Query package and validate user ownership
    query = select(Package).where(Package.id == id, Package.user_id == current_user)
    result = await session.execute(query)
    package = result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found or access denied")
    
    # Update package fields
    update_data = pkg.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(package, field, value)
    
    package.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(package)
    
    return PackageOut(
        id=package.id if package.id is not None else 0,
        user_id=str(package.user_id),
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
        events_count=0,  # TODO: Query for real count
        labels=[],  # TODO: Query for real labels
    )


@router.delete("/{id}")
async def delete_package(
    id: int,
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # TODO: Implement delete package
    return {"success": True}


@router.post("/{id}/refresh")
async def refresh_package(
    id: int,
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # TODO: Implement force refresh tracking
    return {"success": True}


@router.post("/{id}/labels")
async def add_label_to_package(
    id: int,
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # TODO: Implement add label to package
    return {"success": True}


@router.delete("/{id}/labels/{label_id}")
async def remove_label_from_package(
    id: int,
    label_id: int,
    session: AsyncSession = Depends(get_async_session_dep),
    service_name: str = Depends(service_permission_required(["write_shipments"])),
) -> dict:
    # TODO: Implement remove label from package
    return {"success": True}
