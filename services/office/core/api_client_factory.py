"""
API Client Factory module for the Office Service.

This module provides a factory pattern for creating provider-specific API clients
with automatic token management and initialization. It abstracts the complexity
of token retrieval and client instantiation across multiple OAuth providers.
"""

import asyncio
from typing import Dict, List, Optional, Union

from services.api.v1.office import Provider
from services.common.logging_config import get_logger
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.settings import get_settings
from services.office.core.token_manager import TokenManager

# Configure logging
logger = get_logger(__name__)


class APIClientFactory:
    """
    Factory for creating provider-specific API clients.

    Handles token management, client creation, and provider-specific configuration.
    """

    def __init__(self, token_manager: Optional[TokenManager] = None):
        """
        Initialize the API client factory.

        Args:
            token_manager: Optional TokenManager instance. If None, creates a shared instance.
        """
        self._shared_token_manager = token_manager
        self._token_manager_lock = asyncio.Lock()

    async def _get_or_create_token_manager(self) -> TokenManager:
        """
        Get or create a shared TokenManager instance.

        This ensures we reuse the same TokenManager instance across multiple
        create_client() calls, preventing duplicate token requests.
        """
        if self._shared_token_manager is None:
            async with self._token_manager_lock:
                # Double-check pattern to ensure thread safety
                if self._shared_token_manager is None:
                    self._shared_token_manager = TokenManager()

        return self._shared_token_manager

    def set_shared_token_manager(self, token_manager: TokenManager) -> None:
        """
        Set a shared TokenManager instance for dependency injection.

        This allows external code to provide a TokenManager instance,
        useful for testing or when you want to share a TokenManager
        across multiple APIClientFactory instances.

        Args:
            token_manager: TokenManager instance to use
        """
        self._shared_token_manager = token_manager
        logger.info("Shared TokenManager instance set via dependency injection")

    async def create_client(
        self,
        user_id: str,
        provider: Union[str, Provider],
        scopes: Optional[List[str]] = None,
    ) -> Optional[Union[GoogleAPIClient, MicrosoftAPIClient]]:
        """
        Create a provider-specific API client for a user.

        Args:
            user_id: External auth ID to create client for
            provider: Provider name ('google', 'microsoft') or Provider enum
            scopes: Optional list of OAuth scopes. If None, uses default scopes.

        Returns:
            Provider-specific API client instance or None if creation failed
        """
        # Normalize provider to enum
        if isinstance(provider, str):
            try:
                provider = Provider(provider.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid provider: {provider}. Must be 'google' or 'microsoft'"
                )

        # Get default scopes if not provided
        if scopes is None:
            scopes = self._get_default_scopes(provider)

        logger.debug(
            f"Creating {provider} API client for user {user_id} with scopes: {scopes}"
        )

        # Use shared token manager
        token_manager = await self._get_or_create_token_manager()
        logger.debug(
            f"Using shared TokenManager instance for {provider} client (user {user_id})"
        )

        try:
            # Get token from User Management Service
            async with token_manager:
                token_data = await token_manager.get_user_token(
                    user_id, provider.value, scopes
                )

                if token_data is None:
                    logger.warning(
                        f"No token available for user {user_id}, provider {provider}"
                    )
                    return None

                # Create provider-specific client
                client: Union[GoogleAPIClient, MicrosoftAPIClient]
                if provider == Provider.GOOGLE:
                    client = GoogleAPIClient(token_data.access_token, user_id)
                elif provider == Provider.MICROSOFT:
                    client = MicrosoftAPIClient(token_data.access_token, user_id)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")

                logger.debug(
                    f"Successfully created {provider} API client for user {user_id}"
                )
                return client

        except Exception as e:
            logger.error(
                f"Failed to create {provider} API client for user {user_id}: {e}"
            )
            raise

    def _get_default_scopes(self, provider: Provider) -> List[str]:
        """
        Get default OAuth scopes for a provider.

        Args:
            provider: Provider enum

        Returns:
            List of default scopes for the provider
        """
        if provider == Provider.GOOGLE:
            return [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/contacts.readonly",
            ]
        elif provider == Provider.MICROSOFT:
            return [
                "https://graph.microsoft.com/Mail.ReadWrite",
                "https://graph.microsoft.com/Mail.Send",
                "https://graph.microsoft.com/Calendars.ReadWrite",
                "https://graph.microsoft.com/Files.Read",
                "https://graph.microsoft.com/Contacts.Read",
            ]
        else:
            return []

    async def create_google_client(
        self, user_id: str, scopes: Optional[List[str]] = None
    ) -> Optional[GoogleAPIClient]:
        """
        Convenience method to create a Google API client.

        Args:
            user_id: External auth ID to create client for
            scopes: Optional list of OAuth scopes

        Returns:
            GoogleAPIClient instance or None if creation failed
        """
        client = await self.create_client(user_id, Provider.GOOGLE, scopes)
        return client if isinstance(client, GoogleAPIClient) else None

    async def create_microsoft_client(
        self, user_id: str, scopes: Optional[List[str]] = None
    ) -> Optional[MicrosoftAPIClient]:
        """
        Convenience method to create a Microsoft API client.

        Args:
            user_id: External auth ID to create client for
            scopes: Optional list of OAuth scopes

        Returns:
            MicrosoftAPIClient instance or None if creation failed
        """
        client = await self.create_client(user_id, Provider.MICROSOFT, scopes)
        return client if isinstance(client, MicrosoftAPIClient) else None

    async def create_all_clients(
        self, user_id: str, providers: Optional[List[Union[str, Provider]]] = None
    ) -> Dict[Provider, Optional[Union[GoogleAPIClient, MicrosoftAPIClient]]]:
        """
        Create API clients for multiple providers.

        Args:
            user_id: External auth ID to create clients for
            providers: List of providers. If None, creates clients for all providers.

        Returns:
            Dictionary mapping Provider enum to client instances (or None if failed)
        """
        if providers is None:
            providers = [Provider.GOOGLE, Provider.MICROSOFT]

        # Normalize providers to enums
        normalized_providers = []
        for provider in providers:
            if isinstance(provider, str):
                try:
                    normalized_providers.append(Provider(provider.lower()))
                except ValueError:
                    logger.warning(f"Skipping invalid provider: {provider}")
                    continue
            else:
                normalized_providers.append(provider)

        results = {}
        for provider in normalized_providers:
            try:
                client = await self.create_client(user_id, provider)
                results[provider] = client
            except Exception as e:
                logger.error(
                    f"Failed to create {provider} client for user {user_id}: {e}"
                )
                results[provider] = None

        return results

    def get_supported_providers(self) -> List[Provider]:
        """
        Get list of supported providers.

        Returns:
            List of supported Provider enums
        """
        return [Provider.GOOGLE, Provider.MICROSOFT]

    async def get_user_preferred_provider(self, user_id: str) -> Optional[Provider]:
        """
        Get the user's preferred provider from the user service.

        Args:
            user_id: External auth ID to get preferred provider for

        Returns:
            Preferred provider or None if not set
        """
        try:
            # Import here to avoid circular imports
            import httpx

            from services.common.logging_config import request_id_var
            from services.office.core.settings import get_settings

            settings = get_settings()
            if not settings.USER_SERVICE_URL:
                logger.warning(
                    "USER_SERVICE_URL not configured, cannot get preferred provider"
                )
                return None

            # Assert that the API key is set
            assert (
                settings.api_office_user_key is not None
            ), "api_office_user_key must be set in settings for service-to-service authentication"

            # Prepare headers for service-to-service calls
            headers = {"X-API-Key": settings.api_office_user_key}
            request_id = request_id_var.get()
            if request_id and request_id != "uninitialized":
                headers["X-Request-Id"] = request_id

            # Get user profile from user service using internal endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use the internal endpoint to get user by external_auth_id
                response = await client.get(
                    f"{settings.USER_SERVICE_URL}/v1/internal/users/by-external-id/{user_id}",
                    headers=headers,
                )

                if response.status_code == 200:
                    user_data = response.json()

                    if user_data.get("exists"):
                        preferred_provider = user_data.get("preferred_provider")
                        if preferred_provider:
                            try:
                                return Provider(preferred_provider.lower())
                            except ValueError:
                                logger.warning(
                                    f"Invalid preferred provider: {preferred_provider}"
                                )
                                return None
                        else:
                            logger.info(f"No preferred provider set for user {user_id}")
                            return None
                    else:
                        logger.warning(f"User not found for external_auth_id {user_id}")
                        return None
                else:
                    logger.warning(
                        f"Failed to get user profile: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error getting user preferred provider: {e}")
            return None

    async def create_client_for_user(
        self,
        user_id: str,
        scopes: Optional[List[str]] = None,
    ) -> Optional[Union[GoogleAPIClient, MicrosoftAPIClient]]:
        """
        Create a client for a user using their preferred provider.

        Args:
            user_id: External auth ID to create client for
            scopes: Optional list of OAuth scopes

        Returns:
            Initialized API client or None if creation failed
        """
        preferred_provider = await self.get_user_preferred_provider(user_id)
        if not preferred_provider:
            logger.warning(f"No preferred provider found for user {user_id}")
            return None

        return await self.create_client(user_id, preferred_provider, scopes)
