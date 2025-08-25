"""
Office Integration Service for the Contacts Service.

Provides integration with the Office Service to enrich contact data
with office integration information (Google, Microsoft, etc.).
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from services.common.logging_config import get_logger
from services.contacts.settings import get_settings

logger = get_logger(__name__)


class OfficeIntegrationService:
    """Service for integrating with the Office Service to enrich contact data."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.office_service_url = self.settings.OFFICE_SERVICE_URL
        # Use the frontend office key since that's what the Office Service expects
        self.api_key = self.settings.api_frontend_office_key

    async def get_office_contacts(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get contacts from the Office Service for a user.

        Args:
            user_id: ID of the user
            limit: Maximum number of contacts to return
            offset: Number of contacts to skip

        Returns:
            List of office contacts
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.office_service_url}/v1/contacts/",
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json",
                        "X-User-Id": user_id,  # Office Service expects this header
                    },
                    params={
                        "limit": limit,
                        "no_cache": True,  # Get fresh data
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    # Office Service returns ContactList with data field containing contacts
                    contacts = data.get("data", [])
                    logger.info(f"Retrieved {len(contacts)} contacts from Office Service for user {user_id}")
                    return contacts
                else:
                    logger.warning(
                        f"Failed to get office contacts for user {user_id}: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error getting office contacts for user {user_id}: {e}")
            return []

    async def search_office_contacts(
        self, user_id: str, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search contacts in the Office Service for a user.

        Args:
            user_id: ID of the user
            query: Search query
            limit: Maximum number of results

        Returns:
            List of matching office contacts
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.office_service_url}/internal/contacts/search",
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    params={
                        "user_id": user_id,
                        "query": query,
                        "limit": limit,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(
                        f"Failed to search office contacts for user {user_id}: {response.status_code}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Error searching office contacts for user {user_id}: {e}")
            return []

    async def get_office_integration_data(
        self, contacts: List[Any], user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get office integration data for contacts.

        Args:
            contacts: List of contacts to get office data for
            user_id: ID of the user

        Returns:
            Dictionary mapping contact email to office integration data
        """
        if not contacts:
            return {}

        try:
            # Get office contacts for this user
            office_contacts = await self.get_office_contacts(user_id, limit=1000)

            # Create a lookup map for office contacts by email
            office_contact_map = {}
            for office_contact in office_contacts:
                email = office_contact.get("email")
                if email:
                    office_contact_map[email.lower()] = office_contact

            # Create integration data map
            integration_data = {}
            for contact in contacts:
                email = contact.email_address
                if email and email.lower() in office_contact_map:
                    office_contact = office_contact_map[email.lower()]

                    integration_data[email] = {
                        "provider": office_contact.get("provider"),
                        "last_synced": office_contact.get("last_synced"),
                        "source_service": "office",
                        "office_contact_id": office_contact.get("id"),
                        "phone_numbers": office_contact.get("phone_numbers"),
                        "addresses": office_contact.get("addresses"),
                        "notes": office_contact.get("notes"),
                    }
                else:
                    integration_data[email] = {
                        "provider": None,
                        "last_synced": None,
                        "source_service": None,
                        "office_contact_id": None,
                        "phone_numbers": None,
                        "addresses": None,
                        "notes": None,
                    }

            return integration_data

        except Exception as e:
            logger.error(
                f"Error getting office integration data for user {user_id}: {e}"
            )
            # Return empty dict if integration fails
            return {}

    async def get_contact_sync_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get contact synchronization status with the Office Service.

        Args:
            user_id: ID of the user

        Returns:
            Dictionary with sync status information
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.office_service_url}/internal/contacts/stats",
                    headers={
                        "X-API-Key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    params={"user_id": user_id},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "office_contacts_count": data.get("total_contacts", 0),
                        "last_sync": data.get("last_sync"),
                        "sync_status": "active",
                    }
                else:
                    return {
                        "office_contacts_count": 0,
                        "last_sync": None,
                        "sync_status": "error",
                    }

        except Exception as e:
            logger.error(f"Error getting contact sync status for user {user_id}: {e}")
            return {
                "office_contacts_count": 0,
                "last_sync": None,
                "sync_status": "unavailable",
            }
