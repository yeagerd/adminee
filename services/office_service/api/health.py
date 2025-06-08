from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional
from datetime import datetime, timezone # Added import

from models.models import database # For DB check
from core.cache_manager import get_redis_connection # Use redis.asyncio client from cache_manager
from core.token_manager import TokenManager # For integration health check
from schemas.common_schemas import Provider # For provider enum
from core.config import get_settings, Settings # For dependency injection of settings if needed

router = APIRouter(
    prefix="/health",
    tags=["Health & Diagnostics"],
)

# Dependency to get TokenManager instance
def get_token_manager_dependency():
    # This setup implies TokenManager's internal httpx.AsyncClient is created per instance.
    # The close() method on TokenManager is crucial.
    return TokenManager()


@router.get("", summary="Service Health Check")
async def health_check() -> Dict[str, Any]:
    db_healthy = False
    redis_healthy = False

    # Check Database Connection
    try:
        # Ormar's database object might not have a persistent 'is_connected' state
        # that's useful across requests without app-level lifespan management for the connection.
        # Assuming database connection is managed by FastAPI lifespan (not explicitly shown for ormar here yet)
        # or that database.connect()/disconnect() are properly handled if called per-request.
        # For a health check, attempting a simple query is the most reliable.
        if not database.is_connected: # Check initial state
             await database.connect() # Connect if ormar says it's not connected

        await database.execute("SELECT 1")
        db_healthy = True
    except Exception as e:
        # import logging; logging.error(f"Database health check failed: {e}", exc_info=True)
        pass
    # No explicit disconnect here; assuming connection lifecycle is managed elsewhere (e.g. app lifespan or per-request)

    # Check Redis Connection
    redis_client = await get_redis_connection()
    if redis_client:
        try:
            await redis_client.ping()
            redis_healthy = True
        except Exception as e:
            # import logging; logging.error(f"Redis health check failed: {e}", exc_info=True)
            pass

    service_healthy = db_healthy and redis_healthy
    # Return 503 if critical services are down
    # http_status_code = status.HTTP_200_OK if service_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    # Note: FastAPI automatically sets response status code based on exception or default (200 OK).
    # To return 503, one would typically raise HTTPException.
    # For a health check, returning a JSON body indicating health is common, status 200 if endpoint works.
    # Some systems prefer 503 if unhealthy. For now, sticking to JSON response, default 200.

    return {
        "status": "healthy" if service_healthy else "unhealthy",
        "checks": {
            "database_connected": db_healthy,
            "redis_connected": redis_healthy,
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/integrations/{user_id}", summary="User Integrations Health Check")
async def integrations_health_check(
    user_id: str,
    token_manager: TokenManager = Depends(get_token_manager_dependency)
) -> Dict[str, Any]:
    results = {}
    try:
        for provider_enum in Provider: # Iterate over Provider enum (google, microsoft)
            provider_name = provider_enum.value
            try:
                token_data = await token_manager.get_user_token(user_id=user_id, provider=provider_name)
                if token_data and token_data.access_token:
                    # TODO: Optionally, try a lightweight API call with the token for deeper check
                    results[provider_name] = {"status": "connected", "message": "Token retrieved successfully."}
                else:
                    results[provider_name] = {"status": "disconnected", "message": "Failed to retrieve token."}
            except Exception as e:
                # import logging; logging.error(f"Integration check for {provider_name} failed for user {user_id}: {e}", exc_info=True)
                results[provider_name] = {"status": "error", "message": f"Error during token retrieval: {str(e)}"}
    finally:
        # Ensure the TokenManager's httpx client is closed as it's created per-dependency-call
        await token_manager.close()

    return {
        "user_id": user_id,
        "integration_status": results,
        "timestamp": datetime.utcnow().isoformat()
    }
