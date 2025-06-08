import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# Assuming core.config and get_settings are correctly set up from previous steps
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class TokenDataPydantic(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None # Seconds until expiry
    scopes: List[str] = Field(default_factory=list)
    token_type: str = "Bearer"
    # We'll add a retrieved_at timestamp on our side for cache management
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)

class TokenManager:
    def __init__(self, cache_ttl_seconds: int = 300): # Default 5 minutes TTL
        self.http_client = httpx.AsyncClient(timeout=10.0) # 10 second timeout
        self._token_cache: Dict[str, TokenDataPydantic] = {}
        self.cache_ttl_seconds = timedelta(seconds=cache_ttl_seconds)

    async def get_user_token(
        self, user_id: str, provider: str, scopes: Optional[List[str]] = None
    ) -> Optional[TokenDataPydantic]:
        cache_key_parts = [user_id, provider]
        if scopes:
            cache_key_parts.extend(sorted(scopes))
        cache_key = ":".join(cache_key_parts)

        cached_token = self._token_cache.get(cache_key)
        if cached_token:
            # Check our internal cache TTL
            is_cache_ttl_valid = (datetime.utcnow() - cached_token.retrieved_at) < self.cache_ttl_seconds

            # Check token's own expiry if present (with a 60s buffer)
            is_token_expiry_valid = True
            if cached_token.expires_in:
                token_lifetime_seconds = (datetime.utcnow() - cached_token.retrieved_at).total_seconds()
                if token_lifetime_seconds >= (cached_token.expires_in - 60):
                    is_token_expiry_valid = False
                    logger.info(f"Cached token for {user_id}/{provider} nearing its own 'expires_in', needs refresh.")

            if is_cache_ttl_valid and is_token_expiry_valid:
                logger.debug(f"Returning cached token for {user_id} and provider {provider}")
                return cached_token
            else:
                if not is_cache_ttl_valid:
                    logger.info(f"Cached token for {user_id}/{provider} TTL expired, removing.")
                if not is_token_expiry_valid and is_cache_ttl_valid : # Only log if not already logged by TTL expiry
                    logger.info(f"Cached token for {user_id}/{provider} 'expires_in' invalid and removed.")
                del self._token_cache[cache_key]

        logger.info(f"Requesting new token for user {user_id}, provider {provider} from User Management Service.")
        try:
            request_body = {
                "user_id": user_id,
                "provider": provider,
            }
            if scopes:
                request_body["required_scopes"] = scopes

            response = await self.http_client.post(
                f"{settings.USER_MANAGEMENT_SERVICE_URL}/internal/tokens/get",
                json=request_body,
                headers={"Authorization": f"Bearer {settings.SERVICE_API_KEY}"}
            )

            response.raise_for_status()

            token_data_dict = response.json()
            token_data_pydantic = TokenDataPydantic(**token_data_dict, retrieved_at=datetime.utcnow())

            self._token_cache[cache_key] = token_data_pydantic
            logger.info(f"Successfully retrieved and cached token for {user_id}/{provider}.")
            return token_data_pydantic

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error retrieving token for {user_id}/{provider}: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Request error retrieving token for {user_id}/{provider}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving token for {user_id}/{provider}: {e}", exc_info=True)

        return None

    async def close(self):
        await self.http_client.aclose()
