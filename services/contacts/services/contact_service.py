"""
Contact service for business logic operations on contacts.

Provides CRUD operations, search, filtering, and statistics for contacts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select as sqlmodel_select

from services.api.v1.contacts import ContactCreate, EmailContactUpdate
from services.common.http_errors import NotFoundError, ValidationError
from services.common.logging_config import get_logger
from services.contacts.models.contact import Contact
from services.contacts.services.office_integration_service import (
    OfficeIntegrationService,
)

logger = get_logger(__name__)


class ContactService:
    """Service for contact business logic operations."""

    async def create_contact(
        self, session: AsyncSession, contact_data: ContactCreate
    ) -> Contact:
        """Create a new contact."""
        try:
            # Check if contact already exists for this user and email
            existing_contact = await self.get_contact_by_email(
                session, contact_data.user_id, contact_data.email_address
            )

            if existing_contact:
                raise ValidationError(
                    message="Contact already exists for this user and email",
                    field="email_address",
                )

            # Create new contact
            contact = Contact(
                user_id=contact_data.user_id,
                email_address=contact_data.email_address.lower(),
                display_name=contact_data.display_name,
                given_name=contact_data.given_name,
                family_name=contact_data.family_name,
                tags=contact_data.tags or [],
                notes=contact_data.notes,
            )

            # Add to database
            session.add(contact)
            await session.commit()
            await session.refresh(contact)

            logger.info(
                f"Created new contact: {contact.email_address} for user {contact.user_id}"
            )
            return contact

        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            await session.rollback()
            raise

    async def get_contact_by_id(
        self, session: AsyncSession, contact_id: str, user_id: str
    ) -> Optional[Contact]:
        """Get a contact by ID and user ID."""
        try:
            result = await session.execute(
                select(Contact).where(
                    Contact.id == contact_id, Contact.user_id == user_id  # type: ignore
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting contact {contact_id}: {e}")
            return None

    async def get_contact_by_email(
        self, session: AsyncSession, user_id: str, email: str
    ) -> Optional[Contact]:
        """Get a contact by email and user ID."""
        try:
            result = await session.execute(
                select(Contact).where(
                    Contact.user_id == user_id, Contact.email_address == email.lower()  # type: ignore
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting contact by email {email}: {e}")
            return None

    async def list_contacts(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        source_services: Optional[List[str]] = None,
    ) -> List[Contact]:
        """List contacts for a user with optional filtering."""
        try:
            query = select(Contact).where(Contact.user_id == user_id)  # type: ignore

            # Apply filters
            if tags:
                # Filter by tags (contacts must have at least one of the specified tags)
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append(Contact.tags.contains([tag]))  # type: ignore
                query = query.where(or_(*tag_conditions))  # type: ignore

            if source_services:
                # Filter by source services (contacts must have at least one of the specified services)
                service_conditions = []
                for service in source_services:
                    service_conditions.append(
                        Contact.source_services.contains([service])  # type: ignore
                    )
                query = query.where(or_(*service_conditions))  # type: ignore

            # Order by relevance score and apply pagination
            query = (
                query.order_by(desc(Contact.relevance_score))  # type: ignore
                .offset(offset)
                .limit(limit)
            )

            result = await session.execute(query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error listing contacts for user {user_id}: {e}")
            return []

    async def count_contacts(self, session: AsyncSession, user_id: str) -> int:
        """Count total contacts for a user."""
        try:
            result = await session.execute(
                select(func.count()).where(Contact.user_id == user_id)  # type: ignore
            )
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting contacts for user {user_id}: {e}")
            return 0

    async def sync_office_contacts(
        self, session: AsyncSession, user_id: str
    ) -> List[Contact]:
        """
        Sync contacts from Office Service and store them locally.

        This implements the read-through pattern where contacts are fetched
        from the Office Service and stored in the local database for future use.
        """
        try:
            office_service = OfficeIntegrationService()
            # Get office contacts for this user
            office_contacts = await office_service.get_office_contacts(
                user_id, limit=1000
            )
            if not office_contacts:
                logger.info(f"No office contacts found for user {user_id}")
                return []

            synced_contacts = []
            for office_contact in office_contacts:
                try:
                    # Extract email from Office Service contact structure
                    # Office Service Contact has emails list and primary_email
                    primary_email = office_contact.get("primary_email", {})
                    if isinstance(primary_email, dict):
                        email_address = primary_email.get("email", "")
                    else:
                        # Fallback to first email in emails list
                        emails = office_contact.get("emails", [])
                        if emails and isinstance(emails[0], dict):
                            email_address = emails[0].get("email", "")
                        else:
                            email_address = ""

                    if not email_address:
                        logger.warning(
                            f"Office contact has no valid email: {office_contact}"
                        )
                        continue

                    # Check if contact already exists locally
                    existing_contact = await self.get_contact_by_email(
                        session, user_id, email_address
                    )

                    # Extract phone numbers from Office Service contact structure
                    phones = office_contact.get("phones", [])
                    phone_numbers = [
                        phone.get("number", "")
                        for phone in phones
                        if isinstance(phone, dict)
                    ]

                    # Extract notes (combine company and job title)
                    notes_parts = []
                    if office_contact.get("company"):
                        notes_parts.append(f"Company: {office_contact['company']}")
                    if office_contact.get("job_title"):
                        notes_parts.append(f"Job Title: {office_contact['job_title']}")
                    notes = "; ".join(notes_parts) if notes_parts else None

                    if existing_contact:
                        # Update existing contact with office data
                        # Preserve existing source services and add 'office' if not present
                        if "office" not in existing_contact.source_services:
                            existing_contact.source_services.append("office")
                        # Handle provider field properly - avoid converting None to "None"
                        provider_value = office_contact.get("provider")
                        existing_contact.provider = (
                            provider_value if provider_value is not None else None
                        )
                        existing_contact.last_synced = datetime.now(timezone.utc)
                        existing_contact.phone_numbers = phone_numbers
                        existing_contact.notes = notes or existing_contact.notes
                        await session.commit()
                        synced_contacts.append(existing_contact)
                        logger.debug(
                            f"Updated existing contact: {existing_contact.email_address}"
                        )
                    else:
                        # Create new contact from office data
                        # Handle provider field properly - avoid converting None to "None"
                        provider_value = office_contact.get("provider")
                        new_contact = Contact(
                            user_id=user_id,
                            email_address=email_address.lower(),
                            display_name=office_contact.get("full_name")
                            or office_contact.get("given_name"),
                            given_name=office_contact.get("given_name"),
                            family_name=office_contact.get("family_name"),
                            tags=[],  # Office Service doesn't provide tags
                            notes=notes,
                            source_services=["office"],
                            provider=(
                                provider_value if provider_value is not None else None
                            ),
                            last_synced=datetime.now(timezone.utc),
                            phone_numbers=phone_numbers,
                            addresses=[],  # Office Service doesn't provide addresses
                            relevance_score=0.5,  # Default relevance score
                            first_seen=datetime.now(timezone.utc),
                            last_seen=datetime.now(timezone.utc),
                        )
                        session.add(new_contact)
                        await session.commit()
                        await session.refresh(new_contact)
                        synced_contacts.append(new_contact)
                        logger.debug(
                            f"Created new contact from office: {new_contact.email_address}"
                        )

                except Exception as e:
                    logger.error(
                        f"Error syncing office contact {office_contact.get('id', 'unknown')}: {e}"
                    )
                    continue

            logger.info(
                f"Successfully synced {len(synced_contacts)} contacts from Office Service for user {user_id}"
            )
            return synced_contacts

        except Exception as e:
            logger.error(f"Error syncing office contacts for user {user_id}: {e}")
            return []

    async def list_contacts_with_readthrough(
        self,
        session: AsyncSession,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        source_services: Optional[List[str]] = None,
        force_sync: bool = False,
    ) -> List[Contact]:
        """
        List contacts for a user with read-through to Office Service.

        This method implements the read-through pattern:
        1. First returns local contacts
        2. If no local contacts or force_sync=True, syncs from Office Service
        3. Returns combined results
        """
        try:
            # First, get local contacts
            local_contacts = await self.list_contacts(
                session, user_id, limit, offset, tags, source_services
            )

            # If no local contacts or force sync requested, sync from Office Service
            if not local_contacts or force_sync:
                logger.info(f"Syncing contacts from Office Service for user {user_id}")
                synced_contacts = await self.sync_office_contacts(session, user_id)

                # If we synced new contacts, get the updated list
                if synced_contacts:
                    local_contacts = await self.list_contacts(
                        session, user_id, limit, offset, tags, source_services
                    )

            return local_contacts

        except Exception as e:
            logger.error(
                f"Error in read-through contact listing for user {user_id}: {e}"
            )
            # Fall back to local contacts only
            return await self.list_contacts(
                session, user_id, limit, offset, tags, source_services
            )

    async def search_contacts(
        self,
        session: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 20,
        tags: Optional[List[str]] = None,
        source_services: Optional[List[str]] = None,
    ) -> List[Contact]:
        """Search contacts for a user by query."""
        try:
            if not query:
                return await self.list_contacts(
                    session, user_id, limit, tags=tags, source_services=source_services
                )

            query_lower = query.lower()
            base_query = select(Contact).where(
                and_(
                    Contact.user_id == user_id,  # type: ignore
                    (
                        Contact.email_address.ilike(f"%{query_lower}%")  # type: ignore
                        | Contact.display_name.ilike(f"%{query_lower}%")  # type: ignore
                        | Contact.given_name.ilike(f"%{query_lower}%")  # type: ignore
                        | Contact.family_name.ilike(f"%{query_lower}%")  # type: ignore
                    ),
                )
            )

            # Apply filters
            if tags:
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append(Contact.tags.contains([tag]))  # type: ignore
                base_query = base_query.where(or_(*tag_conditions))  # type: ignore

            if source_services:
                service_conditions = []
                for service in source_services:
                    service_conditions.append(
                        Contact.source_services.contains([service])  # type: ignore
                    )
                base_query = base_query.where(or_(*service_conditions))  # type: ignore

            # Order by relevance score and apply limit
            base_query = base_query.order_by(desc(Contact.relevance_score)).limit(  # type: ignore
                limit
            )

            result = await session.execute(base_query)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Error searching contacts for user {user_id}: {e}")
            return []

    async def update_contact(
        self,
        session: AsyncSession,
        contact_id: str,
        user_id: str,
        update_data: EmailContactUpdate,
    ) -> Optional[Contact]:
        """Update an existing contact."""
        try:
            contact = await self.get_contact_by_id(session, contact_id, user_id)
            if not contact:
                return None

            # Apply updates
            if update_data.display_name is not None:
                contact.display_name = update_data.display_name
                # Update derived fields
                contact.given_name = self._extract_given_name(update_data.display_name)
                contact.family_name = self._extract_family_name(
                    update_data.display_name
                )

            if update_data.given_name is not None:
                contact.given_name = update_data.given_name

            if update_data.family_name is not None:
                contact.family_name = update_data.family_name

            if update_data.tags is not None:
                contact.tags = update_data.tags

            if update_data.notes is not None:
                contact.notes = update_data.notes

            # Update timestamps
            from datetime import datetime, timezone

            contact.updated_at = datetime.now(timezone.utc)

            # Recalculate relevance score
            contact.calculate_relevance_score()

            # Update in database
            await session.commit()
            await session.refresh(contact)

            logger.info(f"Updated contact {contact_id}")
            return contact

        except Exception as e:
            logger.error(f"Error updating contact {contact_id}: {e}")
            await session.rollback()
            return None

    async def delete_contact(
        self, session: AsyncSession, contact_id: str, user_id: str
    ) -> bool:
        """Delete a contact."""
        try:
            contact = await self.get_contact_by_id(session, contact_id, user_id)
            if not contact:
                return False

            await session.delete(contact)
            await session.commit()

            logger.info(f"Deleted contact {contact_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting contact {contact_id}: {e}")
            await session.rollback()
            return False

    async def get_contact_stats(
        self, session: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """Get contact statistics for a user."""
        try:
            # Get total contacts
            total_contacts = await self.count_contacts(session, user_id)

            # Get total events
            result = await session.execute(
                select(func.coalesce(func.sum(Contact.total_event_count), 0)).where(
                    Contact.user_id == user_id  # type: ignore
                )
            )
            total_events = result.scalar() or 0

            # Get contacts by source service
            result = await session.execute(
                select(Contact).where(Contact.user_id == user_id)  # type: ignore
            )
            source_services_data = result.scalars().all()

            service_counts: Dict[str, int] = {}
            for contact in source_services_data:
                if hasattr(contact, "source_services") and contact.source_services:
                    for service in contact.source_services:
                        service_counts[service] = service_counts.get(service, 0) + 1

            return {
                "total_contacts": total_contacts,
                "total_events": total_events,
                "by_service": service_counts,
            }

        except Exception as e:
            logger.error(f"Error getting contact stats for user {user_id}: {e}")
            return {
                "total_contacts": 0,
                "total_events": 0,
                "by_service": {},
            }

    def _extract_given_name(self, full_name: str) -> Optional[str]:
        """Extract given name from full name."""
        if not full_name:
            return None

        parts = full_name.strip().split()
        if len(parts) >= 1:
            return parts[0]
        return None

    def _extract_family_name(self, full_name: str) -> Optional[str]:
        """Extract family name from full name."""
        if not full_name:
            return None

        parts = full_name.strip().split()
        if len(parts) >= 2:
            return " ".join(parts[1:])
        return None
