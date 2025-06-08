"""
Health and diagnostics endpoints for the Office Service.

Provides comprehensive health checks for the service and its dependencies,
including database, Redis, and external integrations.
"""

import logging
from datetime import datetime
from typing import Dict, Any
import asyncio

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import httpx

from services.office_service.core.config import settings
from services.office_service.core.cache_manager import cache_manager
from services.office_service.core.token_manager import TokenManager
from services.office_service.models import database
from services.office_service.schemas import ApiResponse

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/health", tags=["health"])

# Initialize dependencies
token_manager = TokenManager()


@router.get("/")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Checks the health of all critical service dependencies:
    - Service status
    - Database connection
    - Redis connection
    - User Management Service connection
    
    Returns:
        JSONResponse: Health status with individual component checks
    """
    start_time = datetime.utcnow()
    checks = {}
    
    try:
        # Check database connection
        checks["database"] = await check_database_connection()
        
        # Check Redis connection
        checks["redis"] = await check_redis_connection()
        
        # Check User Management Service connection
        checks["user_management_service"] = await check_service_connection(
            settings.USER_MANAGEMENT_SERVICE_URL
        )
        
        # Overall health status
        all_healthy = all(checks.values())
        status_code = 200 if all_healthy else 503
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        response_data = {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": start_time.isoformat(),
            "version": settings.APP_VERSION,
            "service": settings.APP_NAME,
            "response_time_ms": response_time_ms,
            "checks": checks
        }
        
        logger.info(f"Health check completed: {response_data['status']}")
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Health check failed with exception: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": start_time.isoformat(),
                "version": settings.APP_VERSION,
                "service": settings.APP_NAME,
                "error": str(e),
                "checks": checks
            }
        )


@router.get("/integrations/{user_id}")
async def integration_health_check(user_id: str):
    """
    Check the health of external integrations for a specific user.
    
    For MVP, this endpoint attempts to fetch tokens for both Google and Microsoft
    providers and reports success or failure for each integration.
    
    Args:
        user_id: ID of the user to check integrations for
        
    Returns:
        JSONResponse: Integration status for each provider
    """
    start_time = datetime.utcnow()
    
    try:
        integration_checks = {}
        
        # Check Google integration
        integration_checks["google"] = await check_user_integration(user_id, "google")
        
        # Check Microsoft integration  
        integration_checks["microsoft"] = await check_user_integration(user_id, "microsoft")
        
        # Overall integration health
        any_healthy = any(check["healthy"] for check in integration_checks.values())
        all_healthy = all(check["healthy"] for check in integration_checks.values())
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        response_data = {
            "user_id": user_id,
            "status": "all_healthy" if all_healthy else ("partial" if any_healthy else "unhealthy"),
            "timestamp": start_time.isoformat(),
            "response_time_ms": response_time_ms,
            "integrations": integration_checks
        }
        
        # Return 200 even if some integrations are unhealthy (partial success is OK)
        status_code = 200
        
        logger.info(f"Integration health check for user {user_id}: {response_data['status']}")
        
        return JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"Integration health check failed for user {user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "user_id": user_id,
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e)
            }
        )


async def check_database_connection() -> bool:
    """
    Check database connectivity and basic operations.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        # Test database connection by executing a simple query
        if database.is_connected:
            # Try to execute a simple query to test the connection
            await database.execute_query("SELECT 1")
            logger.debug("Database health check passed")
            return True
        else:
            # Try to connect
            await database.connect()
            await database.execute_query("SELECT 1")
            logger.debug("Database connection established and health check passed")
            return True
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def check_redis_connection() -> bool:
    """
    Check Redis connectivity and basic operations.
    
    Returns:
        bool: True if Redis is healthy, False otherwise
    """
    try:
        # Use the cache manager's health check method
        is_healthy = await cache_manager.health_check()
        
        if is_healthy:
            logger.debug("Redis health check passed")
        else:
            logger.warning("Redis health check failed")
            
        return is_healthy
        
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


async def check_service_connection(service_url: str) -> bool:
    """
    Check connectivity to an external service.
    
    Args:
        service_url: Base URL of the service to check
        
    Returns:
        bool: True if service is reachable, False otherwise
    """
    try:
        # Create a simple health check URL
        health_url = f"{service_url.rstrip('/')}/health"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(health_url)
            
            # Accept any 2xx or 3xx status as healthy
            is_healthy = 200 <= response.status_code < 400
            
            if is_healthy:
                logger.debug(f"Service health check passed for {service_url}")
            else:
                logger.warning(f"Service health check failed for {service_url}: {response.status_code}")
                
            return is_healthy
            
    except httpx.TimeoutException:
        logger.warning(f"Service health check timeout for {service_url}")
        return False
    except Exception as e:
        logger.error(f"Service health check failed for {service_url}: {e}")
        return False


async def check_user_integration(user_id: str, provider: str) -> Dict[str, Any]:
    """
    Check if a user's integration with a specific provider is working.
    
    Args:
        user_id: ID of the user
        provider: Provider name (google, microsoft)
        
    Returns:
        Dict containing integration health information
    """
    integration_info = {
        "provider": provider,
        "healthy": False,
        "error": None,
        "last_checked": datetime.utcnow().isoformat()
    }
    
    try:
        # Attempt to fetch a token for the user and provider
        # Use minimal scopes for health check
        scopes = ["https://www.googleapis.com/auth/userinfo.profile"] if provider == "google" else ["https://graph.microsoft.com/user.read"]
        token_data = await token_manager.get_user_token(user_id, provider, scopes)
        
        if token_data and token_data.access_token:
            integration_info["healthy"] = True
            integration_info["token_expires_at"] = token_data.expires_at.isoformat() if token_data.expires_at else None
            logger.debug(f"Integration check passed for user {user_id}, provider {provider}")
        else:
            integration_info["error"] = "No valid token available"
            logger.warning(f"Integration check failed for user {user_id}, provider {provider}: No valid token")
            
    except Exception as e:
        integration_info["error"] = str(e)
        logger.error(f"Integration check failed for user {user_id}, provider {provider}: {e}")
    
    return integration_info


@router.get("/quick")
async def quick_health_check():
    """
    Quick health check endpoint for load balancers and basic monitoring.
    
    Returns a simple status without checking external dependencies.
    
    Returns:
        Dict: Basic service status
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    } 