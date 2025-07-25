import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from services.shipments.database import get_async_session_dep
from services.shipments.models import Package
from services.shipments.schemas import (
    PackageCreate,
    PackageListResponse,
    PackageOut,
    PackageUpdate,
)

router = APIRouter()


@router.get("/", response_model=PackageListResponse)
async def list_packages(session: AsyncSession = Depends(get_async_session_dep)) -> dict:
    logging.info("Fetching all packages from DB...")
    result = await session.execute(select(Package))
    packages = result.scalars().all()
    logging.info(f"Found {len(packages)} packages")
    # Convert to PackageOut (minimal fields for now)
    package_out = [
        PackageOut(
            id=pkg.id if pkg.id is not None else 0,
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
    pkg: PackageCreate, session: AsyncSession = Depends(get_async_session_dep)
) -> PackageOut:
    db_pkg = Package(**pkg.dict())
    session.add(db_pkg)
    await session.commit()
    await session.refresh(db_pkg)
    return PackageOut(
        id=db_pkg.id if db_pkg.id is not None else 0,
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
    id: int, session: AsyncSession = Depends(get_async_session_dep)
) -> PackageOut:
    # TODO: Implement get package details
    # For now, return a dummy response
    return PackageOut(
        id=id,
        tracking_number="dummy",
        carrier="dummy",
        status="pending",
        estimated_delivery=None,
        actual_delivery=None,
        recipient_name=None,
        shipper_name=None,
        package_description=None,
        order_number=None,
        tracking_link=None,
        updated_at=datetime.utcnow(),
        events_count=0,
        labels=[],
    )


@router.put("/{id}", response_model=PackageOut)
async def update_package(
    id: int, pkg: PackageUpdate, session: AsyncSession = Depends(get_async_session_dep)
) -> PackageOut:
    # TODO: Implement update package
    return PackageOut(
        id=id,
        tracking_number="dummy",
        carrier="dummy",
        status="pending",
        estimated_delivery=None,
        actual_delivery=None,
        recipient_name=None,
        shipper_name=None,
        package_description=None,
        order_number=None,
        tracking_link=None,
        updated_at=datetime.utcnow(),
        events_count=0,
        labels=[],
    )


@router.delete("/{id}")
async def delete_package(
    id: int, session: AsyncSession = Depends(get_async_session_dep)
) -> dict:
    # TODO: Implement delete package
    return {"success": True}


@router.post("/{id}/refresh")
async def refresh_package(
    id: int, session: AsyncSession = Depends(get_async_session_dep)
) -> dict:
    # TODO: Implement force refresh tracking
    return {"success": True}


@router.post("/{id}/labels")
async def add_label_to_package(
    id: int, session: AsyncSession = Depends(get_async_session_dep)
) -> dict:
    # TODO: Implement add label to package
    return {"success": True}


@router.delete("/{id}/labels/{label_id}")
async def remove_label_from_package(
    id: int, label_id: int, session: AsyncSession = Depends(get_async_session_dep)
) -> dict:
    # TODO: Implement remove label from package
    return {"success": True}
