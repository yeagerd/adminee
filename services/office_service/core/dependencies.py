from fastapi import Depends
from typing import Annotated, Optional

from .token_manager import TokenManager
from .api_client_factory import APIClientFactory

_token_manager_instance: Optional[TokenManager] = None
_api_client_factory_instance: Optional[APIClientFactory] = None

async def get_token_manager() -> TokenManager:
    global _token_manager_instance
    if _token_manager_instance is None:
        _token_manager_instance = TokenManager()
    return _token_manager_instance

async def get_api_client_factory(
    token_manager: Annotated[TokenManager, Depends(get_token_manager)]
) -> APIClientFactory:
    global _api_client_factory_instance
    if _api_client_factory_instance is None:
        _api_client_factory_instance = APIClientFactory(token_manager=token_manager)
    return _api_client_factory_instance

async def close_global_token_manager():
    global _token_manager_instance
    if _token_manager_instance:
        await _token_manager_instance.close()
        _token_manager_instance = None
