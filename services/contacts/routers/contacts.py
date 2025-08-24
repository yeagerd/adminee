"""
Contact API endpoints for the Contacts Service.

Provides RESTful API for contact CRUD operations, search, and statistics.
Follows the same pattern as other services:
- User-facing endpoints use /me and extract user from JWT (no user_id in path/query)
- Internal endpoints use /internal and require API key authentication
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.http_errors import NotFoundError, ValidationError
from services.common.logging_config import get_logger
from services.contacts.auth import (
    get_current_user,
    service_permission_required,
)
from services.contacts.database import get_async_session
from services.contacts.models.contact import Contact
from services.contacts.schemas.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactSearchRequest,
    ContactStatsResponse,
    EmailContactSearchResult,
    EmailContactUpdate,
)
from services.contacts.services.contact_discovery_service import ContactDiscoveryService
from services.contacts.services.contact_service import ContactService
from services.contacts.services.office_integration_service import (
    OfficeIntegrationService,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/contacts", tags=["contacts"])


async def get_contact_service() -> ContactService:
    """Get contact service instance."""
    return ContactService()


async def get_contact_discovery_service() -> ContactDiscoveryService:
    """Get contact discovery service instance."""
    from services.common.pubsub_client import PubSubClient

    pubsub_client = (
        PubSubClient()
    )  # Simplified - in real implementation, this would be injected
    return ContactDiscoveryService(pubsub_client)


async def get_office_integration_service() -> OfficeIntegrationService:
    """Get office integration service instance."""
    return OfficeIntegrationService()


@router.get("/me", response_model=ContactListResponse)
async def list_my_contacts(
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of contacts to return"
    ),
    offset: int = Query(0, ge=0, description="Number of contacts to skip"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    source_services: Optional[List[str]] = Query(
        None, description="Filter by source services"
    ),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    office_integration_service: OfficeIntegrationService = Depends(
        get_office_integration_service
    ),
    authenticated_service: str = Depends(
        service_permission_required(["read_contacts"])
    ),
    current_user_id: str = Depends(get_current_user),
) -> ContactListResponse:
    """List contacts for the currently authenticated user with optional filtering."""
    try:
        contacts = await contact_service.list_contacts(
            session=session,
            user_id=current_user_id,
            limit=limit,
            offset=offset,
            tags=tags,
            source_services=source_services,
        )

        # Get office integration data for contacts
        office_integration_data = (
            await office_integration_service.get_office_integration_data(
                contacts, current_user_id
            )
        )

        total = await contact_service.count_contacts(
            session=session, user_id=current_user_id
        )

        return ContactListResponse(
            contacts=contacts,
            total=total,
            limit=limit,
            offset=offset,
            success=True,
        )
    except Exception as e:
        logger.error(f"Error listing contacts for user {current_user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list contacts")


@router.get("/me/search", response_model=List[EmailContactSearchResult])
async def search_my_contacts(
    query: str = Query(..., description="Search query for name or email"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    source_services: Optional[List[str]] = Query(
        None, description="Filter by source services"
    ),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    office_integration_service: OfficeIntegrationService = Depends(
        get_office_integration_service
    ),
    authenticated_service: str = Depends(
        service_permission_required(["search_contacts"])
    ),
    current_user_id: str = Depends(get_current_user),
) -> List[EmailContactSearchResult]:
    """Search contacts for the currently authenticated user by query."""
    try:
        contacts = await contact_service.search_contacts(
            session=session,
            user_id=current_user_id,
            query=query,
            limit=limit,
            tags=tags,
            source_services=source_services,
        )

        # Get office integration data for contacts
        office_integration_data = (
            await office_integration_service.get_office_integration_data(
                contacts, current_user_id
            )
        )

        # Convert to search results with relevance scores
        results = []
        for contact in contacts:
            result = EmailContactSearchResult(
                contact=contact,
                relevance_score=contact.relevance_score,
                match_highlights=[
                    query
                ],  # Simplified - could implement actual highlighting
            )
            results.append(result)

        return results
    except Exception as e:
        logger.error(f"Error searching contacts for user {current_user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to search contacts")


@router.get("/me/stats", response_model=ContactStatsResponse)
async def get_my_contact_stats(
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    office_integration_service: OfficeIntegrationService = Depends(
        get_office_integration_service
    ),
    authenticated_service: str = Depends(
        service_permission_required(["read_contact_stats"])
    ),
    current_user_id: str = Depends(get_current_user),
) -> ContactStatsResponse:
    """Get contact statistics for the currently authenticated user."""
    try:
        stats = await contact_service.get_contact_stats(
            session=session, user_id=current_user_id
        )

        # Get office integration sync status
        office_sync_status = await office_integration_service.get_contact_sync_status(
            current_user_id
        )

        # Add office integration info to stats
        stats["office_integration"] = office_sync_status

        return ContactStatsResponse(
            total_contacts=stats["total_contacts"],
            total_events=stats["total_events"],
            by_service=stats["by_service"],
            success=True,
        )
    except Exception as e:
        logger.error(f"Error getting contact stats for user {current_user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contact statistics")


@router.get("/me/{contact_id}", response_model=ContactResponse)
async def get_my_contact(
    contact_id: str = Path(..., description="Contact ID to retrieve"),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    office_integration_service: OfficeIntegrationService = Depends(
        get_office_integration_service
    ),
    authenticated_service: str = Depends(
        service_permission_required(["read_contacts"])
    ),
    current_user_id: str = Depends(get_current_user),
) -> ContactResponse:
    """Get a specific contact by ID for the currently authenticated user."""
    try:
        contact = await contact_service.get_contact_by_id(
            session=session, contact_id=contact_id, user_id=current_user_id
        )

        if not contact:
            raise NotFoundError("Contact", contact_id)

        # Get office integration data for contact
        office_integration_data = (
            await office_integration_service.get_office_integration_data(
                [contact], current_user_id
            )
        )

        return ContactResponse(contact=contact, success=True)
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contact")


@router.post("/me", response_model=ContactResponse, status_code=201)
async def create_my_contact(
    contact_data: ContactCreate,
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(
        service_permission_required(["write_contacts"])
    ),
    current_user_id: str = Depends(get_current_user),
) -> ContactResponse:
    """Create a new contact for the currently authenticated user."""
    try:
        # Ensure the contact is created for the current user
        contact_data.user_id = current_user_id

        contact = await contact_service.create_contact(
            session=session, contact_data=contact_data
        )

        return ContactResponse(
            contact=contact, success=True, message="Contact created successfully"
        )
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Error creating contact: {e}")
        raise HTTPException(status_code=500, detail="Failed to create contact")


@router.put("/me/{contact_id}")
async def update_my_contact(
    contact_id: str = Path(..., description="Contact ID to update"),
    update_data: EmailContactUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(
        service_permission_required(["write_contacts"])
    ),
    current_user_id: str = Depends(get_current_user),
) -> ContactResponse:
    """Update an existing contact for the currently authenticated user."""
    try:
        contact = await contact_service.update_contact(
            session=session,
            contact_id=contact_id,
            user_id=current_user_id,
            update_data=update_data,
        )

        if not contact:
            raise NotFoundError("Contact", contact_id)

        return ContactResponse(
            contact=contact, success=True, message="Contact updated successfully"
        )
    except NotFoundError:
        raise
    except ValidationError as e:
        raise
    except Exception as e:
        logger.error(f"Error updating contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update contact")


@router.delete("/me/{contact_id}")
async def delete_my_contact(
    contact_id: str = Path(..., description="Contact ID to delete"),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(
        service_permission_required(["write_contacts"])
    ),
    current_user_id: str = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a contact for the currently authenticated user."""
    try:
        success = await contact_service.delete_contact(
            session=session, contact_id=contact_id, user_id=current_user_id
        )

        if not success:
            raise NotFoundError("Contact", contact_id)

        return {"success": True, "message": "Contact deleted successfully"}
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete contact")
