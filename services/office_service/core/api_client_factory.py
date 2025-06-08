import logging
from typing import Optional, List, Union, Dict
from services.office_service.models import Provider
from services.office_service.core.token_manager import TokenManager
from services.office_service.core.clients.base import BaseAPIClient
from services.office_service.core.clients.google import GoogleAPIClient
from services.office_service.core.clients.microsoft import MicrosoftAPIClient

# Configure logging
logger = logging.getLogger(__name__)

class APIClientFactory:
    """
    Factory class for creating provider-specific API clients.
    
    This factory handles:
    - Token retrieval from User Management Service via TokenManager
    - Provider-specific client instantiation
    - Error handling for token and client creation failures
    """
    
    def __init__(self, token_manager: Optional[TokenManager] = None):
        """
        Initialize the API client factory.
        
        Args:
            token_manager: Optional TokenManager instance. If None, will create one.
        """
        self.token_manager = token_manager
    
    async def create_client(
        self, 
        user_id: str, 
        provider: Union[str, Provider], 
        scopes: Optional[List[str]] = None
    ) -> Optional[BaseAPIClient]:
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
                raise ValueError(f"Invalid provider: {provider}. Must be 'google' or 'microsoft'")
        
        # Set default scopes based on provider
        if scopes is None:
            scopes = self._get_default_scopes(provider)
        
        logger.info(f"Creating {provider} API client for user {user_id} with scopes: {scopes}")
        
        # Use provided token manager or create a new one
        token_manager = self.token_manager
        if token_manager is None:
            token_manager = TokenManager()
        
        try:
            # Get token from User Management Service
            async with token_manager:
                token_data = await token_manager.get_user_token(user_id, provider.value, scopes)
                
                if token_data is None:
                    logger.warning(f"No token available for user {user_id}, provider {provider}")
                    return None
                
                # Create provider-specific client
                if provider == Provider.GOOGLE:
                    client = GoogleAPIClient(token_data.access_token, user_id)
                elif provider == Provider.MICROSOFT:
                    client = MicrosoftAPIClient(token_data.access_token, user_id)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
                
                logger.info(f"Successfully created {provider} API client for user {user_id}")
                return client
                
        except Exception as e:
            logger.error(f"Failed to create {provider} API client for user {user_id}: {e}")
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
                "https://www.googleapis.com/auth/drive.readonly"
            ]
        elif provider == Provider.MICROSOFT:
            return [
                "https://graph.microsoft.com/Mail.Read",
                "https://graph.microsoft.com/Mail.Send",
                "https://graph.microsoft.com/Calendars.ReadWrite",
                "https://graph.microsoft.com/Files.Read"
            ]
        else:
            return []
    
    async def create_google_client(
        self, 
        user_id: str, 
        scopes: Optional[List[str]] = None
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
        self, 
        user_id: str, 
        scopes: Optional[List[str]] = None
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
        self, 
        user_id: str, 
        providers: Optional[List[Union[str, Provider]]] = None
    ) -> Dict[Provider, Optional[BaseAPIClient]]:
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
                logger.error(f"Failed to create {provider} client for user {user_id}: {e}")
                results[provider] = None
        
        return results
    
    def get_supported_providers(self) -> List[Provider]:
        """
        Get list of supported providers.
        
        Returns:
            List of supported Provider enums
        """
        return [Provider.GOOGLE, Provider.MICROSOFT] 