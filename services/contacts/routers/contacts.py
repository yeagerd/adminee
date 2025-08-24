"""
Contact API endpoints for the Contacts Service.

Provides RESTful API for contact CRUD operations, search, and statistics.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.http_errors import NotFoundError, ValidationError
from services.common.logging_config import get_logger
from services.contacts.auth import require_frontend_auth, require_user_service_auth
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


@router.get("/", response_model=ContactListResponse)
async def list_contacts(
    user_id: str = Query(..., description="User ID to get contacts for"),
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
    authenticated_service: str = Depends(require_frontend_auth),
) -> ContactListResponse:
    """List contacts for a user with optional filtering."""
    try:
        contacts = await contact_service.list_contacts(
            session=session,
            user_id=user_id,
            limit=limit,
            offset=offset,
            tags=tags,
            source_services=source_services,
        )

        total = await contact_service.count_contacts(session=session, user_id=user_id)

        return ContactListResponse(
            contacts=contacts,
            total=total,
            limit=limit,
            offset=offset,
            success=True,
        )
    except Exception as e:
        logger.error(f"Error listing contacts for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list contacts")


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str = Path(..., description="Contact ID to retrieve"),
    user_id: str = Query(..., description="User ID who owns the contact"),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(require_frontend_auth),
) -> ContactResponse:
    """Get a specific contact by ID."""
    try:
        contact = await contact_service.get_contact_by_id(
            session=session, contact_id=contact_id, user_id=user_id
        )

        if not contact:
            raise NotFoundError("Contact", contact_id)

        return ContactResponse(contact=contact, success=True)
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error getting contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contact")


@router.post("/", response_model=ContactResponse, status_code=201)
async def create_contact(
    contact_data: ContactCreate,
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(require_frontend_auth),
) -> ContactResponse:
    """Create a new contact."""
    try:
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


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str = Path(..., description="Contact ID to update"),
    user_id: str = Query(..., description="User ID who owns the contact"),
    update_data: EmailContactUpdate = ...,
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(require_frontend_auth),
) -> ContactResponse:
    """Update an existing contact."""
    try:
        contact = await contact_service.update_contact(
            session=session,
            contact_id=contact_id,
            user_id=user_id,
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


@router.delete("/{contact_id}")
async def delete_contact(
    contact_id: str = Path(..., description="Contact ID to delete"),
    user_id: str = Query(..., description="User ID who owns the contact"),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(require_frontend_auth),
):
    """Delete a contact."""
    try:
        success = await contact_service.delete_contact(
            session=session, contact_id=contact_id, user_id=user_id
        )

        if not success:
            raise NotFoundError("Contact", contact_id)

        return {"success": True, "message": "Contact deleted successfully"}
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error deleting contact {contact_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete contact")


@router.get("/search", response_model=List[EmailContactSearchResult])
async def search_contacts(
    user_id: str = Query(..., description="User ID to search contacts for"),
    query: str = Query(..., description="Search query for name or email"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    source_services: Optional[List[str]] = Query(
        None, description="Filter by source services"
    ),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(require_frontend_auth),
) -> List[EmailContactSearchResult]:
    """Search contacts for a user by query."""
    try:
        contacts = await contact_service.search_contacts(
            session=session,
            user_id=user_id,
            query=query,
            limit=limit,
            tags=tags,
            source_services=source_services,
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
        logger.error(f"Error searching contacts for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to search contacts")


@router.get("/stats", response_model=ContactStatsResponse)
async def get_contact_stats(
    user_id: str = Query(..., description="User ID to get stats for"),
    session: AsyncSession = Depends(get_async_session),
    contact_service: ContactService = Depends(get_contact_service),
    authenticated_service: str = Depends(require_frontend_auth),
) -> ContactStatsResponse:
    """Get contact statistics for a user."""
    try:
        stats = await contact_service.get_contact_stats(
            session=session, user_id=user_id
        )

        return ContactStatsResponse(
            total_contacts=stats["total_contacts"],
            total_events=stats["total_events"],
            by_service=stats["by_service"],
            success=True,
        )
    except Exception as e:
        logger.error(f"Error getting contact stats for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get contact statistics")
