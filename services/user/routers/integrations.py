"""
OAuth integrations management router.

Handles OAuth flow management, integration status, token operations,
and provider configuration with comprehensive authentication and validation.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from services.user.auth.clerk import get_current_user, verify_user_ownership
from services.user.exceptions import (
    IntegrationException,
    NotFoundException,
    SimpleValidationException,
)
from services.user.models.integration import (
    IntegrationProvider,
    IntegrationStatus,
)
from services.user.schemas.integration import (
    IntegrationDisconnectRequest,
    IntegrationDisconnectResponse,
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationProviderInfo,
    IntegrationStatsResponse,
    OAuthCallbackRequest,
    OAuthCallbackResponse,
    OAuthStartRequest,
    OAuthStartResponse,
    ProviderListResponse,
    ScopeValidationRequest,
    ScopeValidationResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
)
from services.user.services.audit_service import audit_logger
from services.user.services.integration_service import (
    get_integration_service,
)

router = APIRouter(
    prefix="/users/{user_id}/integrations",
    tags=["Integrations"],
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Access forbidden - insufficient permissions"},
        404: {"description": "User or integration not found"},
        422: {"description": "Validation error"},
    },
)

# Separate router for provider-level endpoints (no user_id)
provider_router = APIRouter(
    prefix="/integrations",
    tags=["Integration Providers"],
    responses={
        401: {"description": "Authentication required"},
        422: {"description": "Validation error"},
    },
)


@router.get("/", response_model=IntegrationListResponse)
async def list_user_integrations(
    user_id: str,
    provider: Optional[IntegrationProvider] = Query(
        None, description="Filter by provider"
    ),
    integration_status: Optional[IntegrationStatus] = Query(
        None, description="Filter by status", alias="status"
    ),
    include_token_info: bool = Query(True, description="Include token metadata"),
    current_user: str = Depends(get_current_user),
):
    """
    List all integrations for a user.

    Returns comprehensive integration information including status, metadata,
    token availability, and error details with optional filtering.

    **Query Parameters:**
    - `provider`: Filter integrations by specific OAuth provider
    - `status`: Filter integrations by status (active, inactive, error, pending)
    - `include_token_info`: Include token expiration and availability info

    **Response includes:**
    - Integration details and provider information
    - OAuth scope information and external user data
    - Token metadata (expiration, availability) without actual tokens
    - Error information and health status
    - Last sync timestamps and activity
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    try:
        return await get_integration_service().get_user_integrations(
            user_id=user_id,
            provider=provider,
            status=integration_status,
            include_token_info=include_token_info,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SimpleValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except IntegrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/oauth/start", response_model=OAuthStartResponse)
async def start_oauth_flow(
    user_id: str,
    request: OAuthStartRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Start OAuth authorization flow for a provider.

    Initiates the OAuth 2.0 authorization code flow with PKCE security.
    Returns authorization URL that the client should redirect the user to.

    **Security Features:**
    - PKCE challenge/verifier generation
    - Secure state parameter with expiration
    - Scope validation and provider verification
    - User-specific encryption keys

    **Request Body:**
    - `provider`: OAuth provider (google, microsoft, etc.)
    - `redirect_uri`: OAuth callback URL (must be whitelisted)
    - `scopes`: Requested OAuth scopes (optional, uses defaults)
    - `state_data`: Additional data to preserve through flow

    **Response:**
    - `authorization_url`: URL to redirect user for authorization
    - `state`: OAuth state parameter (preserve for callback)
    - `expires_at`: State expiration time
    - `requested_scopes`: Final scope list that will be requested
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    try:
        return await get_integration_service().start_oauth_flow(
            user_id=user_id,
            provider=request.provider,
            redirect_uri=request.redirect_uri,
            scopes=request.scopes,
            state_data=request.state_data,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SimpleValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except IntegrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.post("/oauth/callback", response_model=OAuthCallbackResponse)
async def complete_oauth_flow(
    user_id: str,
    request: OAuthCallbackRequest,
    provider: IntegrationProvider = Query(..., description="OAuth provider"),
    current_user: str = Depends(get_current_user),
):
    """
    Complete OAuth authorization flow and create integration.

    Handles the OAuth callback with authorization code exchange, token storage,
    and integration setup. Creates or updates the user's integration record.

    **Security Features:**
    - State validation and anti-CSRF protection
    - Secure token storage with user-specific encryption
    - Comprehensive error handling and logging
    - Integration status tracking

    **Request Body:**
    - `code`: Authorization code from OAuth provider
    - `state`: OAuth state parameter from start flow
    - `error`: OAuth error code (if authorization failed)
    - `error_description`: Human-readable error description

    **Response:**
    - `success`: Whether OAuth flow completed successfully
    - `integration_id`: Created/updated integration ID
    - `status`: Integration status after completion
    - `scopes`: Actually granted OAuth scopes
    - `external_user_info`: User information from provider
    - `error`: Error message if flow failed
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    try:
        # Handle OAuth errors from provider
        if request.error:
            await audit_logger.log_security_event(
                user_id=user_id,
                action="oauth_callback_error",
                severity="medium",
                details={
                    "provider": provider.value,
                    "error": request.error,
                    "error_description": request.error_description,
                },
            )
            return OAuthCallbackResponse(
                success=False,
                integration_id=None,
                provider=provider,
                status=IntegrationStatus.ERROR,
                scopes=[],
                external_user_info=None,
                error=f"OAuth error: {request.error} - {request.error_description}",
            )

        # Complete the OAuth flow
        result = await get_integration_service().complete_oauth_flow(
            user_id=user_id,
            provider=provider,
            authorization_code=request.code,
            state=request.state,
        )

        # If the service returned an error result, still return it as 200 with success=False
        return result

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SimpleValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get("/stats", response_model=IntegrationStatsResponse)
async def get_integration_statistics(
    user_id: str,
    current_user: str = Depends(get_current_user),
):
    """
    Get comprehensive integration statistics for user.

    Provides analytics and metrics about all user integrations including
    status distribution, provider usage, error tracking, and sync activity.

    **Statistics Include:**
    - Total integration counts by status and provider
    - Recent error history and patterns
    - Synchronization activity and timestamps
    - Health metrics and trends

    **Response:**
    - Counts by status (active, error, pending, etc.)
    - Counts by provider (Google, Microsoft, etc.)
    - Recent errors with timestamps and details
    - Sync statistics and activity metrics
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    try:
        return await get_integration_service().get_integration_statistics(
            user_id=user_id
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/{provider}")
async def get_specific_integration(
    user_id: str,
    provider: IntegrationProvider,
    current_user: str = Depends(get_current_user),
):
    """
    Get details for a specific integration.

    Returns detailed information about a specific provider integration
    including status, token info, scopes, and metadata.

    **Response includes:**
    - Integration status and provider information
    - Token availability and expiration details
    - OAuth scopes and external user information
    - Error details and health status
    - Last sync timestamps and activity
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    try:
        # Get all integrations and filter for the specific provider
        integrations_response = await get_integration_service().get_user_integrations(
            user_id=user_id,
            provider=provider,
            include_token_info=True,
        )

        if not integrations_response.integrations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration not found for provider: {provider.value}",
            )

        # Return the first (and should be only) integration for this provider
        return integrations_response.integrations[0]

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except SimpleValidationException as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except IntegrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.delete("/{provider}", response_model=IntegrationDisconnectResponse)
async def disconnect_integration(
    user_id: str,
    provider: IntegrationProvider,
    request: IntegrationDisconnectRequest | None = None,
    current_user: str = Depends(get_current_user),
):
    """
    Disconnect an OAuth integration.

    Removes the integration connection and optionally revokes tokens with
    the provider and deletes associated data.

    **Request Body (optional):**
    - `revoke_tokens`: Whether to revoke tokens with provider (default: true)
    - `delete_data`: Whether to permanently delete integration data (default: false)

    **Response:**
    - `success`: Whether disconnection completed successfully
    - `tokens_revoked`: Whether tokens were successfully revoked
    - `data_deleted`: Whether integration data was deleted
    - `disconnected_at`: Timestamp of disconnection
    - `error`: Error message if disconnection failed
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    if request is None:
        request = IntegrationDisconnectRequest()

    try:
        result = await get_integration_service().disconnect_integration(
            user_id=user_id,
            provider=provider,
            revoke_tokens=request.revoke_tokens,
            delete_data=request.delete_data,
        )

        return IntegrationDisconnectResponse(**result)

    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.put("/{provider}/refresh", response_model=TokenRefreshResponse)
async def refresh_integration_tokens(
    user_id: str,
    provider: IntegrationProvider,
    request: TokenRefreshRequest = None,
    current_user: str = Depends(get_current_user),
):
    """
    Refresh access tokens for an integration.

    Manually refresh OAuth access tokens using stored refresh tokens.
    Typically used when tokens are near expiration or after API errors.

    **Request Body (optional):**
    - `force`: Force refresh even if token not near expiration (default: false)

    **Response:**
    - `success`: Whether token refresh completed successfully
    - `token_expires_at`: New token expiration time
    - `refreshed_at`: Timestamp of refresh operation
    - `error`: Error message if refresh failed
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    if request is None:
        request = TokenRefreshRequest()

    try:
        result = await get_integration_service().refresh_integration_tokens(
            user_id=user_id,
            provider=provider,
            force=request.force,
        )

        return result
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrationException as e:
        # Return a failed TokenRefreshResponse instead of raising HTTP error
        return TokenRefreshResponse(
            success=False,
            integration_id=None,
            provider=provider,
            token_expires_at=None,
            refreshed_at=datetime.now(timezone.utc),
            error=str(e),
        )


@router.get("/{provider}/health", response_model=IntegrationHealthResponse)
async def check_integration_health(
    user_id: str,
    provider: IntegrationProvider,
    current_user: str = Depends(get_current_user),
):
    """
    Check the health status of an integration.

    Performs comprehensive health checks including token validity,
    connection status, and recent activity analysis.

    **Health Checks:**
    - Integration status and error state
    - Token validity and expiration
    - Recent synchronization activity
    - Provider connectivity

    **Response:**
    - `healthy`: Overall health status boolean
    - `issues`: List of identified problems
    - `recommendations`: Suggested actions to resolve issues
    - `last_check_at`: Timestamp of health check
    """
    # Verify user can access this resource
    await verify_user_ownership(current_user, user_id)

    try:
        return await get_integration_service().check_integration_health(
            user_id=user_id,
            provider=provider,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IntegrationException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# Provider-level endpoints (no user_id required)


@provider_router.get("/providers", response_model=ProviderListResponse)
async def list_oauth_providers(
    current_user: str = Depends(get_current_user),
):
    """
    List all available OAuth providers.

    Returns configuration information for all supported OAuth providers
    including availability status, supported scopes, and default settings.

    **Response:**
    - Provider display names and identifiers
    - Availability status (configured and enabled)
    - Supported OAuth scopes with descriptions
    - Default scope configurations
    """
    try:
        oauth_config = get_integration_service().oauth_config
        providers = []

        for provider in IntegrationProvider:
            if oauth_config.is_provider_available(provider):
                provider_config = oauth_config.get_provider_config(provider)

                # Get scope information
                supported_scopes = []
                for scope_name, scope_info in provider_config.scope_definitions.items():
                    supported_scopes.append(
                        {
                            "name": scope_name,
                            "description": scope_info.get("description", ""),
                            "required": scope_info.get("required", False),
                            "sensitive": scope_info.get("sensitive", False),
                            "granted": False,  # Not applicable for provider listing
                        }
                    )

                provider_info = IntegrationProviderInfo(
                    name=provider_config.name,
                    provider=provider,
                    available=True,
                    supported_scopes=supported_scopes,
                    default_scopes=provider_config.default_scopes,
                )
                providers.append(provider_info)

        return ProviderListResponse(
            providers=providers,
            total=len(providers),
            available_count=len(providers),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list providers: {str(e)}",
        )


@provider_router.post("/validate-scopes", response_model=ScopeValidationResponse)
async def validate_oauth_scopes(
    request: ScopeValidationRequest,
    current_user: str = Depends(get_current_user),
):
    """
    Validate OAuth scopes for a provider.

    Checks requested scopes against provider configuration and returns
    validation results with warnings and recommendations.

    **Request Body:**
    - `provider`: OAuth provider to validate against
    - `scopes`: List of scope names to validate

    **Response:**
    - `valid_scopes`: Scopes that are supported by provider
    - `invalid_scopes`: Scopes that are not supported
    - `required_scopes`: Required scopes that will be automatically added
    - `sensitive_scopes`: Scopes that access sensitive data
    - `warnings`: Validation warnings and recommendations
    """
    try:
        oauth_config = get_integration_service().oauth_config

        if not oauth_config.is_provider_available(request.provider):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Provider {request.provider.value} is not available",
            )

        provider_config = oauth_config.get_provider_config(request.provider)
        valid_scopes, invalid_scopes = provider_config.validate_scopes(request.scopes)

        # Identify scope types
        required_scopes = [
            s
            for s in valid_scopes
            if provider_config.scope_definitions.get(s, {}).get("required", False)
        ]
        sensitive_scopes = [
            s
            for s in valid_scopes
            if provider_config.scope_definitions.get(s, {}).get("sensitive", False)
        ]

        # Generate warnings
        warnings = []
        if invalid_scopes:
            warnings.append(
                f"Invalid scopes will be ignored: {', '.join(invalid_scopes)}"
            )
        if sensitive_scopes:
            warnings.append(
                f"Sensitive scopes requested: {', '.join(sensitive_scopes)}"
            )
        if len(valid_scopes) > 10:
            warnings.append(
                "Large number of scopes requested - consider using fewer scopes"
            )

        return ScopeValidationResponse(
            provider=request.provider,
            requested_scopes=request.scopes,
            valid_scopes=valid_scopes,
            invalid_scopes=invalid_scopes,
            required_scopes=required_scopes,
            sensitive_scopes=sensitive_scopes,
            warnings=warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate scopes: {str(e)}",
        )


# Include both routers
def get_integration_routers():
    """Get both integration routers for main app registration."""
    return [router, provider_router]
