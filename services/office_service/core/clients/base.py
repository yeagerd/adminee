import httpx
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class BaseAPIClient:
    def __init__(self, access_token: str, client: Optional[httpx.AsyncClient] = None):
        self._access_token = access_token
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None # Flag to know if we need to close it

    @property
    def headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        logger.debug(f"Making {method} request to {url} with headers {self.headers} and params {kwargs.get('params')}")
        try:
            response = await self._client.request(method, url, headers=self.headers, **kwargs)
            logger.debug(f"Response from {url}: {response.status_code}")
            # Basic check for success, specific clients might want to override or add more detail
            # response.raise_for_status() # This could be too generic here, let specific methods handle
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {method} {url}: {e.response.status_code} - {e.response.text}")
            raise # Re-raise for specific client handling or global error handler
        except httpx.RequestError as e:
            logger.error(f"Request error for {method} {url}: {e}")
            raise

    async def close(self):
        if self._owns_client:
            await self._client.aclose()
            logger.debug("Owned httpx.AsyncClient closed.")
