"""
Token service for User Management Service.

Provides secure token storage, retrieval, and lifecycle management for
internal service-to-service communication with automatic refresh and validation.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import structlog

from ..exceptions import (
    IntegrationException,
    NotFoundException,
)
from ..models.integration import Integration, IntegrationProvider, IntegrationStatus
from ..models.token import EncryptedToken, TokenType
from ..models.user import User
from ..schemas.integration import (
    InternalTokenResponse,
    InternalUserStatusResponse,
)
from ..security.encryption import TokenEncryption
from ..services.audit_service import audit_logger
from ..services.integration_service import integration_service

# Set up logging
logger = structlog.get_logger(__name__)


class TokenService:
    """
    Service for managing encrypted token storage and retrieval.

    Handles secure token operations for service-to-service communication
    including automatic refresh, scope validation, and lifecycle management.
    """

    def __init__(self):
        """Initialize the token service."""
        self.token_encryption = TokenEncryption()
        self.logger = logger

    async def store_tokens(
        self,
        user_id: str,
        provider: IntegrationProvider,
        tokens: Dict[str, str],
        scopes: Optional[List[str]] = None,
    ) -> None:
        """
        Store encrypted tokens for a user integration.

        Args:
            user_id: User identifier
            provider: OAuth provider
            tokens: Dictionary containing access_token and optional refresh_token
            scopes: OAuth scopes associated with the tokens

        Raises:
            NotFoundException: If user or integration not found
            IntegrationException: If token storage fails
        """
        try:
            # Get user integration
            integration = await self._get_user_integration(user_id, provider)

            # Encrypt access token
            encrypted_access = self.token_encryption.encrypt_token(
                token=tokens["access_token"],
                user_id=user_id,
            )

            # Encrypt refresh token if provided
            encrypted_refresh = None
            if tokens.get("refresh_token"):
                encrypted_refresh = self.token_encryption.encrypt_token(
                    token=tokens["refresh_token"],
                    user_id=user_id,
                )

            # Calculate expiration
            expires_at = None
            if tokens.get("expires_in"):
                expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=int(tokens["expires_in"])
                )

            # Store access token
            await self._store_token_record(
                integration=integration,
                token_type=TokenType.ACCESS,
                encrypted_value=encrypted_access,
                expires_at=expires_at,
                scopes=scopes,
            )

            # Store refresh token if provided
            if encrypted_refresh:
                await self._store_token_record(
                    integration=integration,
                    token_type=TokenType.REFRESH,
                    encrypted_value=encrypted_refresh,
                    expires_at=None,  # Refresh tokens usually don't expire
                    scopes=scopes,
                )

            await audit_logger.log_user_action(
                user_id=user_id,
                action="tokens_stored",
                resource_type="token",
                details={
                    "provider": provider.value,
                    "integration_id": integration.id,
                    "has_refresh_token": bool(tokens.get("refresh_token")),
                    "expires_at": expires_at.isoformat() if expires_at else None,
                },
            )

            self.logger.info(
                "Tokens stored successfully",
                user_id=user_id,
                provider=provider.value,
                integration_id=integration.id,
            )

        except Exception as e:
            self.logger.error(
                "Failed to store tokens",
                user_id=user_id,
                provider=provider.value,
                error=str(e),
            )
            if isinstance(e, (NotFoundException, IntegrationException)):
                raise
            raise IntegrationException(f"Failed to store tokens: {str(e)}")

    async def get_valid_token(
        self,
        user_id: str,
        provider: IntegrationProvider,
        required_scopes: Optional[List[str]] = None,
        refresh_if_needed: bool = True,
    ) -> InternalTokenResponse:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            user_id: User identifier
            provider: OAuth provider
            required_scopes: Required OAuth scopes
            refresh_if_needed: Whether to auto-refresh if near expiration

        Returns:
            InternalTokenResponse with token data or error

        Raises:
            NotFoundException: If user or integration not found
        """
        try:
            # Get user integration
            integration = await self._get_user_integration(user_id, provider)

            # Check if integration is active
            if integration.status != IntegrationStatus.ACTIVE:
                return InternalTokenResponse(
                    success=False,
                    provider=provider,
                    user_id=user_id,
                    integration_id=integration.id,
                    error=f"Integration status is {integration.status.value}",
                )

            # Get access token record
            access_token_record = await EncryptedToken.objects.get_or_none(
                integration=integration, token_type=TokenType.ACCESS
            )
            if not access_token_record:
                return InternalTokenResponse(
                    success=False,
                    provider=provider,
                    user_id=user_id,
                    integration_id=integration.id,
                    error="No access token found",
                )

            # Check token expiration
            now = datetime.now(timezone.utc)
            buffer_time = timedelta(minutes=5)

            if (
                access_token_record.expires_at
                and access_token_record.expires_at <= now + buffer_time
                and refresh_if_needed
            ):
                # Token is expired or near expiration - try to refresh
                refresh_result = await self._refresh_token_if_possible(
                    integration, user_id, provider
                )
                if refresh_result.success:
                    # Get the refreshed access token record
                    access_token_record = await EncryptedToken.objects.get(
                        integration=integration, token_type=TokenType.ACCESS
                    )
                else:
                    return InternalTokenResponse(
                        success=False,
                        provider=provider,
                        user_id=user_id,
                        integration_id=integration.id,
                        error=f"Token refresh failed: {refresh_result.error}",
                    )

            # Decrypt access token
            access_token = self.token_encryption.decrypt_token(
                encrypted_token=access_token_record.encrypted_value,
                user_id=user_id,
            )

            # Get refresh token if available
            refresh_token = None
            refresh_token_record = await EncryptedToken.objects.get_or_none(
                integration=integration, token_type=TokenType.REFRESH
            )
            if refresh_token_record:
                refresh_token = self.token_encryption.decrypt_token(
                    encrypted_token=refresh_token_record.encrypted_value,
                    user_id=user_id,
                )

            # Validate scopes if required
            granted_scopes = (
                list(integration.scopes.keys()) if integration.scopes else []
            )
            if required_scopes and not self._has_required_scopes(
                granted_scopes, required_scopes
            ):
                return InternalTokenResponse(
                    success=False,
                    provider=provider,
                    user_id=user_id,
                    integration_id=integration.id,
                    scopes=granted_scopes,
                    error=f"Insufficient scopes. Required: {required_scopes}, Granted: {granted_scopes}",
                )

            await audit_logger.log_user_action(
                user_id=user_id,
                action="token_retrieved",
                resource_type="token",
                details={
                    "provider": provider.value,
                    "integration_id": integration.id,
                    "required_scopes": required_scopes,
                    "granted_scopes": granted_scopes,
                },
            )

            return InternalTokenResponse(
                success=True,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=access_token_record.expires_at,
                scopes=granted_scopes,
                provider=provider,
                user_id=user_id,
                integration_id=integration.id,
            )

        except Exception as e:
            self.logger.error(
                "Failed to get valid token",
                user_id=user_id,
                provider=provider.value,
                error=str(e),
            )
            if isinstance(e, NotFoundException):
                raise
            return InternalTokenResponse(
                success=False,
                provider=provider,
                user_id=user_id,
                error=f"Token retrieval failed: {str(e)}",
            )

    async def refresh_tokens(
        self,
        user_id: str,
        provider: IntegrationProvider,
        force: bool = False,
    ) -> InternalTokenResponse:
        """
        Manually refresh tokens for a user integration.

        Args:
            user_id: User identifier
            provider: OAuth provider
            force: Force refresh even if not near expiration

        Returns:
            InternalTokenResponse with refresh status
        """
        try:
            # Use integration service for refresh
            refresh_result = await integration_service.refresh_integration_tokens(
                user_id=user_id,
                provider=provider,
                force=force,
            )

            if refresh_result.success:
                # Get the updated token
                return await self.get_valid_token(
                    user_id=user_id,
                    provider=provider,
                    refresh_if_needed=False,
                )
            else:
                return InternalTokenResponse(
                    success=False,
                    provider=provider,
                    user_id=user_id,
                    integration_id=refresh_result.integration_id,
                    error=refresh_result.error,
                )

        except Exception as e:
            self.logger.error(
                "Failed to refresh tokens",
                user_id=user_id,
                provider=provider.value,
                error=str(e),
            )
            return InternalTokenResponse(
                success=False,
                provider=provider,
                user_id=user_id,
                error=f"Token refresh failed: {str(e)}",
            )

    async def get_user_status(self, user_id: str) -> InternalUserStatusResponse:
        """
        Get user integration status for internal services.

        Args:
            user_id: User identifier

        Returns:
            InternalUserStatusResponse with user status
        """
        try:
            # Verify user exists
            user = await User.objects.get_or_none(clerk_id=user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Get all user integrations
            integrations = await Integration.objects.filter(
                user__clerk_id=user_id
            ).all()

            # Calculate statistics
            total_integrations = len(integrations)
            active_integrations = sum(
                1 for i in integrations if i.status == IntegrationStatus.ACTIVE
            )
            providers = [i.provider for i in integrations]
            has_errors = any(i.status == IntegrationStatus.ERROR for i in integrations)

            # Find latest sync time
            last_sync_at = None
            if integrations:
                sync_times = [i.last_sync_at for i in integrations if i.last_sync_at]
                if sync_times:
                    last_sync_at = max(sync_times)

            return InternalUserStatusResponse(
                user_id=user_id,
                active_integrations=active_integrations,
                total_integrations=total_integrations,
                providers=providers,
                has_errors=has_errors,
                last_sync_at=last_sync_at,
            )

        except Exception as e:
            self.logger.error(
                "Failed to get user status",
                user_id=user_id,
                error=str(e),
            )
            if isinstance(e, NotFoundException):
                raise
            raise IntegrationException(f"Failed to get user status: {str(e)}")

    async def _get_user_integration(
        self, user_id: str, provider: IntegrationProvider
    ) -> Integration:
        """Get user integration by user ID and provider."""
        integration = await Integration.objects.select_related("user").get_or_none(
            user__clerk_id=user_id, provider=provider
        )
        if not integration:
            raise NotFoundException(
                f"Integration not found for user {user_id} and provider {provider.value}"
            )
        return integration

    async def _store_token_record(
        self,
        integration: Integration,
        token_type: TokenType,
        encrypted_value: str,
        expires_at: Optional[datetime],
        scopes: Optional[List[str]],
    ) -> None:
        """Store or update a token record."""
        # Check if token record exists
        existing_record = await EncryptedToken.objects.get_or_none(
            integration=integration, token_type=token_type
        )

        scopes_dict = {scope: True for scope in scopes} if scopes else None

        if existing_record:
            await existing_record.update(
                encrypted_value=encrypted_value,
                expires_at=expires_at,
                scopes=scopes_dict,
                updated_at=datetime.now(timezone.utc),
            )
        else:
            await EncryptedToken.objects.create(
                user=integration.user,
                integration=integration,
                token_type=token_type,
                encrypted_value=encrypted_value,
                expires_at=expires_at,
                scopes=scopes_dict,
            )

    async def _refresh_token_if_possible(
        self, integration: Integration, user_id: str, provider: IntegrationProvider
    ):
        """Refresh token if refresh token is available."""
        try:
            return await integration_service.refresh_integration_tokens(
                user_id=user_id,
                provider=provider,
                force=True,
            )
        except Exception as e:
            self.logger.warning(
                "Token refresh failed",
                user_id=user_id,
                provider=provider.value,
                error=str(e),
            )
            # Return a failed response similar to TokenRefreshResponse
            from ..schemas.integration import TokenRefreshResponse

            return TokenRefreshResponse(
                success=False,
                integration_id=integration.id,
                provider=provider,
                token_expires_at=None,
                refreshed_at=datetime.now(timezone.utc),
                error=str(e),
            )

    def _has_required_scopes(
        self, granted_scopes: List[str], required_scopes: List[str]
    ) -> bool:
        """Check if granted scopes include all required scopes."""
        return all(scope in granted_scopes for scope in required_scopes)


# Global token service instance
token_service = TokenService()
