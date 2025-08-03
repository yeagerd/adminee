"""
Event service for handling tracking event interactions with packages
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from services.shipments.models import Package, TrackingEvent, utc_now
from services.shipments.schemas import TrackingEventOut


class EventService:
    """Service for handling tracking event operations"""

    @staticmethod
    async def create_initial_event(
        session: AsyncSession,
        package_id: UUID,
        status: str,
        email_message_id: Optional[str] = None,
    ) -> TrackingEventOut:
        """Create an initial tracking event when a package is created"""
        initial_event = TrackingEvent(
            package_id=package_id,
            event_date=utc_now(),
            status=status,
            location=None,
            description=f"Package tracking initiated - Status: {status}",
            email_message_id=email_message_id,
        )
        session.add(initial_event)
        await session.commit()
        await session.refresh(initial_event)

        return TrackingEventOut(
            id=initial_event.id,
            event_date=initial_event.event_date,
            status=initial_event.status,
            location=initial_event.location,
            description=initial_event.description,
            created_at=initial_event.created_at,
        )

    @staticmethod
    async def get_events_count(session: AsyncSession, package_id: UUID) -> int:
        """Get the count of tracking events for a package"""
        events_query = select(TrackingEvent).where(
            TrackingEvent.package_id == package_id
        )
        events_result = await session.execute(events_query)
        events = events_result.scalars().all()
        return len(events)

    @staticmethod
    async def delete_package_events(session: AsyncSession, package_id: UUID) -> None:
        """Delete all tracking events for a package"""
        events_query = select(TrackingEvent).where(
            TrackingEvent.package_id == package_id
        )
        events_result = await session.execute(events_query)
        events = events_result.scalars().all()

        for event in events:
            await session.delete(event)
        await session.commit()

    @staticmethod
    async def create_event_if_email_exists(
        session: AsyncSession,
        package_id: UUID,
        email_message_id: str,
        status: str,
        event_date: Optional[datetime] = None,
    ) -> Optional[TrackingEventOut]:
        """Create a tracking event if one doesn't exist for the given email_message_id"""
        if not email_message_id:
            return None

        # Check if an event with this email_message_id already exists for this package
        existing_event_query = select(TrackingEvent).where(
            TrackingEvent.email_message_id == email_message_id,
            TrackingEvent.package_id == package_id,
        )
        existing_event_result = await session.execute(existing_event_query)
        existing_event = existing_event_result.scalar_one_or_none()

        if existing_event:
            return None  # Event already exists

        # Create new event
        new_event = TrackingEvent(
            package_id=package_id,
            event_date=event_date or utc_now(),
            status=status,
            location=None,
            description=f"Package updated - Status: {status}",
            email_message_id=email_message_id,
        )
        session.add(new_event)
        await session.commit()
        await session.refresh(new_event)

        return TrackingEventOut(
            id=new_event.id,
            event_date=new_event.event_date,
            status=new_event.status,
            location=new_event.location,
            description=new_event.description,
            created_at=new_event.created_at,
        )

    @staticmethod
    async def get_events_by_email_message_id(
        session: AsyncSession, email_message_id: str, user_id: str
    ) -> List[TrackingEventOut]:
        """Get tracking events by email message ID for a specific user"""
        events_query = (
            select(TrackingEvent)
            .join(Package, TrackingEvent.package_id == Package.id)
            .where(
                TrackingEvent.email_message_id == email_message_id,
                Package.user_id == user_id,
            )
            .order_by(TrackingEvent.event_date.desc())
        )
        events_result = await session.execute(events_query)
        events = events_result.scalars().all()

        return [
            TrackingEventOut(
                id=event.id,
                event_date=event.event_date,
                status=event.status,
                location=event.location,
                description=event.description,
                created_at=event.created_at,
            )
            for event in events
        ]

    @staticmethod
    async def get_package_ids_by_email_message_id(
        session: AsyncSession, email_message_id: str, user_id: str
    ) -> List[UUID]:
        """Get package IDs by email message ID for a specific user"""
        events_query = (
            select(TrackingEvent.package_id)
            .join(Package, TrackingEvent.package_id == Package.id)  # type: ignore
            .where(
                TrackingEvent.email_message_id == email_message_id,
                Package.user_id == user_id,
            )
            .distinct()
        )
        events_result = await session.execute(events_query)
        package_ids = events_result.scalars().all()
        return list(package_ids)
