"""
Service client for chat service to communicate with other services.

Provides HTTP client functionality to call User Management Service and Office Service
with proper authentication using API keys.
"""

import types
from typing import Any, Dict, List, Optional, Type

import httpx

from services.chat.settings import get_settings
from services.common.logging_config import get_logger, request_id_var

logger = get_logger(__name__)


class ServiceClient:
    """HTTP client for service-to-service communication."""

    def __init__(self):
        self.timeout = httpx.Timeout(30.0)

    async def __aenter__(self) -> "ServiceClient":
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[types.TracebackType]) -> None:  # type: ignore[override]
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.aclose()
        return None

    def _get_headers_for_service(self, service_name: str) -> Dict[str, str]:
        """Get authentication headers for a specific service."""
        headers = {"Content-Type": "application/json"}

        # Propagate request ID for distributed tracing
        request_id = request_id_var.get()
        if request_id and request_id != "uninitialized":
            headers["X-Request-Id"] = request_id

        if service_name == "user-management" and get_settings().api_chat_user_key:
            headers["X-API-Key"] = get_settings().api_chat_user_key  # type: ignore[assignment]
        elif service_name == "office" and get_settings().api_chat_office_key:
            headers["X-API-Key"] = get_settings().api_chat_office_key  # type: ignore[assignment]

        return headers

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from User Management Service."""
        try:
            headers = self._get_headers_for_service("user-management")

            url = get_settings().user_management_service_url or ""  # type: ignore[assignment]
            response = await self.http_client.get(
                f"{url}/users/{user_id}",
                headers=headers,
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f"User {user_id} not found")
                return None
            else:
                logger.error(
                    f"Failed to get user info: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting user info for {user_id}: {e}")
            return None

    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences from User Management Service using internal endpoint."""
        try:
            headers = self._get_headers_for_service("user-management")

            url = get_settings().user_management_service_url or ""  # type: ignore[assignment]
            response = await self.http_client.get(
                f"{url}/internal/users/{user_id}/preferences",
                headers=headers,
            )

            if response.status_code == 200:
                # Handle both null response and preferences object
                result = response.json()
                return result if result is not None else None
            elif response.status_code == 404:
                logger.info(
                    f"Preferences for user {user_id} not found - normal for new users"
                )
                return None
            else:
                logger.error(
                    f"Failed to get user preferences: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting user preferences for {user_id}: {e}")
            return None

    async def get_calendar_events(
        self, user_id: str, days_ahead: int = 7
    ) -> Optional[List[Dict[str, Any]]]:
        """Get calendar events from Office Service."""
        try:
            headers = self._get_headers_for_service("office")

            response = await self.http_client.get(
                f"{get_settings().office_service_url}/calendar/events?user_id={user_id}&days_ahead={days_ahead}",
                headers=headers,
            )

            if response.status_code == 200:
                return response.json().get("data", [])
            else:
                logger.error(
                    f"Failed to get calendar events: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting calendar events for {user_id}: {e}")
            return None

    async def get_files(
        self, user_id: str, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """Get files from Office Service."""
        try:
            headers = self._get_headers_for_service("office")

            response = await self.http_client.get(
                f"{get_settings().office_service_url}/files?user_id={user_id}&limit={limit}",
                headers=headers,
            )

            if response.status_code == 200:
                return response.json().get("data", {}).get("files", [])
            else:
                logger.error(
                    f"Failed to get files: {response.status_code} - {response.text}"
                )
                return None

        except Exception as e:
            logger.error(f"Error getting files for {user_id}: {e}")
            return None


# Global service client instance
service_client = ServiceClient()
