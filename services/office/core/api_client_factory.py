"""
API Client Factory module for the Office Service.

This module provides a factory pattern for creating provider-specific API clients
with automatic token management and initialization. It abstracts the complexity
of token retrieval and client instantiation across multiple OAuth providers.
"""

from typing import Dict, List, Optional, Union

from services.common.logging_config import get_logger
from services.office.core.clients.google import GoogleAPIClient
from services.office.core.clients.microsoft import MicrosoftAPIClient
from services.office.core.demo_token_manager import DemoTokenManager
from services.office.core.settings import get_settings
from services.office.core.token_manager import TokenManager
from services.office.models import Provider

# Configure logging
logger = get_logger(__name__)


class APIClientFactory:
    """
    Factory class for creating provider-specific API clients.

    This factory handles:
    - Token retrieval from User Management Service via TokenManager
    - Provider-specific client instantiation
    - Error handling for token and client creation failures
    - Demo mode support using environment variables instead of user service
    """

    def __init__(self, token_manager: Optional[TokenManager] = None):
        """
        Initialize the API client factory.

        Args:
            token_manager: Optional TokenManager instance. If None, will create one
                          based on DEMO_MODE setting.
        """
        self.token_manager = token_manager

    async def create_client(
        self,
        user_id: str,
        provider: Union[str, Provider],
        scopes: Optional[List[str]] = None,
    ) -> Optional[Union[GoogleAPIClient, MicrosoftAPIClient]]:
        """
        Create a provider-specific API client for a user.

        Args:
            user_id: User ID to create client for
            provider: Provider name ('google', 'microsoft') or Provider enum
            scopes: Optional list of OAuth scopes. If None, uses default scopes.

        Returns:
            Initialized API client or None if creation failed

        Raises:
            ValueError: For invalid provider
            Exception: For other creation failures
        """
        # Normalize provider to enum
        if isinstance(provider, str):
            try:
                provider = Provider(provider.lower())
            except ValueError:
                raise ValueError(
                    f"Invalid provider: {provider}. Must be 'google' or 'microsoft'"
                )

        # Set default scopes based on provider
        if scopes is None:
            scopes = self._get_default_scopes(provider)

        logger.info(
            f"Creating {provider} API client for user {user_id} with scopes: {scopes}"
        )

        # Use provided token manager or create a new one
        token_manager = self.token_manager
        if token_manager is None:
            if get_settings().DEMO_MODE:
                logger.info("Demo mode enabled - using DemoTokenManager")
                token_manager = DemoTokenManager()
            else:
                token_manager = TokenManager()

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

                logger.info(
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
            ]
        elif provider == Provider.MICROSOFT:
            return [
                "https://graph.microsoft.com/Mail.Read",
                "https://graph.microsoft.com/Mail.Send",
                "https://graph.microsoft.com/Calendars.ReadWrite",
                "https://graph.microsoft.com/Files.Read",
            ]
        else:
            return []

    async def create_google_client(
        self, user_id: str, scopes: Optional[List[str]] = None
    ) -> Optional[GoogleAPIClient]:
        """
        Convenience method to create a Google API client.

        Args:
            user_id: User ID to create client for
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
            user_id: User ID to create client for
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
            user_id: User ID to create clients for
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
            user_id: User ID to get preferred provider for (external_auth_id or internal ID)

        Returns:
            Preferred provider or None if not set
        """
        try:
            # Import here to avoid circular imports
            import httpx

            from services.common.logging_config import request_id_var
            from services.office.core.settings import get_settings

            settings = get_settings()
            if not settings.USER_MANAGEMENT_SERVICE_URL:
                logger.warning(
                    "USER_MANAGEMENT_SERVICE_URL not configured, cannot get preferred provider"
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

            # If user_id is not an integer, resolve to internal ID
            resolved_user_id = user_id
            try:
                int(user_id)
            except ValueError:
                # Not an integer, resolve
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{settings.USER_MANAGEMENT_SERVICE_URL}/users/id?external_auth_id={user_id}",
                        headers=headers,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        resolved_user_id = str(data.get("id"))
                        logger.info(
                            f"Resolved external_auth_id {user_id} to internal user ID {resolved_user_id}"
                        )
                    else:
                        logger.warning(
                            f"Failed to resolve internal user ID for external_auth_id {user_id}: {resp.status_code}"
                        )
                        return None

            # Get user profile from user service using internal ID
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{settings.USER_MANAGEMENT_SERVICE_URL}/users/{resolved_user_id}",
                    headers=headers,
                )

                if response.status_code == 200:
                    user_data = response.json()
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
                        logger.info(
                            f"No preferred provider set for user {resolved_user_id}"
                        )
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
            user_id: User ID to create client for
            scopes: Optional list of OAuth scopes

        Returns:
            Initialized API client or None if creation failed
        """
        preferred_provider = await self.get_user_preferred_provider(user_id)
        if not preferred_provider:
            logger.warning(f"No preferred provider found for user {user_id}")
            return None

        return await self.create_client(user_id, preferred_provider, scopes)
