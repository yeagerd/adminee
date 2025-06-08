import logging
from typing import Optional, Union, List
from .token_manager import TokenManager, TokenDataPydantic
from .clients.google import GoogleAPIClient
from .clients.microsoft import MicrosoftAPIClient
from .clients.base import BaseAPIClient # For type hinting primarily
from schemas.common_schemas import Provider # To use the Provider enum

logger = logging.getLogger(__name__)

class APIClientFactory:
    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager

    async def get_client(
        self, user_id: str, provider: Provider, scopes: Optional[List[str]] = None
    ) -> Optional[Union[GoogleAPIClient, MicrosoftAPIClient]]:

        token_data: Optional[TokenDataPydantic] = await self._token_manager.get_user_token(
            user_id=user_id, provider=provider.value, scopes=scopes
        )

        if not token_data or not token_data.access_token:
            logger.error(f"Failed to retrieve token for user {user_id}, provider {provider.value}")
            return None

        if provider == Provider.GOOGLE:
            logger.info(f"Creating GoogleAPIClient for user {user_id}")
            return GoogleAPIClient(access_token=token_data.access_token)
        elif provider == Provider.MICROSOFT:
            logger.info(f"Creating MicrosoftAPIClient for user {user_id}")
            return MicrosoftAPIClient(access_token=token_data.access_token)
        else:
            logger.warning(f"Unknown provider: {provider} requested for API client factory.")
            return None

        # Optional: A method to get multiple clients, e.g., for parallel calls
        # async def get_clients_for_providers(self, user_id: str, providers: List[Provider], scopes: Optional[Dict[Provider, List[str]]] = None): ...
