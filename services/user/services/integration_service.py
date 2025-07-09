"""
Integration service for User Management Service.

Provides comprehensive OAuth integration management including provider configuration,
token handling, lifecycle management, and health monitoring.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import structlog
from sqlmodel import select

from services.user.database import get_async_session
from services.user.exceptions import (
    IntegrationException,
    NotFoundException,
    SimpleValidationException,
)
from services.user.integrations.oauth_config import get_oauth_config
from services.user.models.integration import (
    Integration,
    IntegrationProvider,
    IntegrationStatus,
)
from services.user.models.token import EncryptedToken, TokenType
from services.user.models.user import User
from services.user.schemas.integration import (
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationResponse,
    IntegrationStatsResponse,
    OAuthCallbackResponse,
    OAuthStartResponse,
    TokenRefreshResponse,
)
from services.user.security.encryption import TokenEncryption
from services.user.services.audit_service import get_audit_logger

# Set up logging
logger = structlog.get_logger(__name__)


class IntegrationService:
    """
    Service for managing OAuth integrations.

    Handles the complete OAuth lifecycle including authorization, token management,
    refresh operations, and integration health monitoring.
    """

    def __init__(self):
        """Initialize the integration service."""
        self.oauth_config = get_oauth_config()
        self.token_encryption = TokenEncryption()
        self.logger = logger

    async def get_user_integrations(
        self,
        user_id: str,
        provider: Optional[IntegrationProvider] = None,
        status: Optional[IntegrationStatus] = None,
        include_token_info: bool = True,
    ) -> IntegrationListResponse:
        """
        Get all integrations for a user with optional filtering.

        Args:
            user_id: User identifier
            provider: Filter by specific provider (optional)
            status: Filter by integration status (optional)
            include_token_info: Whether to include token metadata

        Returns:
            IntegrationListResponse with user's integrations

        Raises:
            NotFoundException: If user not found
        """
        try:
            # Verify user exists
            async_session = get_async_session()
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.external_auth_id == user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    raise NotFoundException(f"User not found: {user_id}")

            # Build query for integrations within the same session
            async_session = get_async_session()
            async with async_session() as session:
                query = select(Integration).where(Integration.user_id == user.id)

                if provider:
                    query = query.where(Integration.provider == provider)
                if status:
                    query = query.where(Integration.status == status)

                # Get integrations
                integrations_result = await session.execute(query)
                integrations = list(integrations_result.scalars().all())

                # Convert to response models
                integration_responses = []
                for integration in integrations:
                    token_info = {}
                    if include_token_info:
                        token_info = await self._get_token_metadata(integration.id)

                    integration_response = IntegrationResponse(
                        id=integration.id,
                        user_id=user.external_auth_id,  # Use the user from the session
                        provider=integration.provider,
                        status=integration.status,
                        scopes=(
                            list(integration.scopes.keys())
                            if integration.scopes
                            else []
                        ),
                        external_user_id=integration.provider_user_id,
                        external_email=integration.provider_email,
                        external_name=(
                            integration.provider_metadata.get("name")
                            if integration.provider_metadata
                            else None
                        ),
                        has_access_token=token_info.get("has_access_token", False),
                        has_refresh_token=token_info.get("has_refresh_token", False),
                        token_expires_at=token_info.get("expires_at"),
                        token_created_at=token_info.get("created_at"),
                        last_sync_at=integration.last_sync_at,
                        last_error=integration.error_message,
                        error_count=await self._get_error_count(integration.id),
                        created_at=integration.created_at,
                        updated_at=integration.updated_at,
                    )
                    integration_responses.append(integration_response)

            # Calculate statistics
            total = len(integration_responses)
            active_count = sum(
                1 for i in integration_responses if i.status == IntegrationStatus.ACTIVE
            )
            error_count = sum(
                1 for i in integration_responses if i.status == IntegrationStatus.ERROR
            )

            await get_audit_logger().log_user_action(
                user_id=user_id,
                action="integrations_listed",
                resource_type="integration",
                details={
                    "total_integrations": total,
                    "active_count": active_count,
                    "error_count": error_count,
                    "provider_filter": provider.value if provider else None,
                    "status_filter": status.value if status else None,
                },
            )

            return IntegrationListResponse(
                integrations=integration_responses,
                total=total,
                active_count=active_count,
                error_count=error_count,
            )

        except Exception as e:
            self.logger.error(
                "Failed to get user integrations",
                user_id=user_id,
                provider=provider,
                status=status,
                error=str(e),
            )
            if isinstance(e, (NotFoundException, SimpleValidationException)):
                raise
            raise IntegrationException(f"Failed to get integrations: {str(e)}")

    async def start_oauth_flow(
        self,
        user_id: str,
        provider: IntegrationProvider,
        redirect_uri: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        state_data: Optional[Dict[str, Any]] = None,
    ) -> OAuthStartResponse:
        """
        Start OAuth authorization flow for a provider.

        Args:
            user_id: User identifier
            provider: OAuth provider
            redirect_uri: OAuth callback URL (optional, uses default if not provided)
            scopes: Requested OAuth scopes (optional)
            state_data: Additional state data (optional)

        Returns:
            OAuthStartResponse with authorization URL and state

        Raises:
            NotFoundException: If user not found
            SimpleValidationException: If provider not available or invalid scopes
        """
        try:
            # Verify user exists
            async_session = get_async_session()
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.external_auth_id == user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    raise NotFoundException(f"User not found: {user_id}")

            # Check if provider is available
            if not self.oauth_config.is_provider_available(provider):
                raise SimpleValidationException(
                    f"Provider {provider.value} is not available"
                )

            # Get provider config to validate and use default scopes
            provider_config = self.oauth_config.get_provider_config(provider)
            if not provider_config:
                raise SimpleValidationException(
                    f"Provider {provider.value} configuration not found"
                )

            # Use provided scopes or default scopes from provider config
            request_scopes = scopes or provider_config.default_scopes.copy()

            # Use provided redirect_uri or default from config
            final_redirect_uri = (
                redirect_uri or self.oauth_config.get_default_redirect_uri()
            )

            # Generate real authorization URL using OAuth config
            authorization_url, oauth_state = (
                self.oauth_config.generate_authorization_url(
                    provider=provider,
                    user_id=user_id,
                    redirect_uri=final_redirect_uri,
                    scopes=request_scopes,
                    extra_params=state_data,
                )
            )

            # Log the OAuth flow start
            await get_audit_logger().log_user_action(
                user_id=user_id,
                action="oauth_flow_started",
                resource_type="integration",
                details={
                    "provider": provider.value,
                    "redirect_uri": final_redirect_uri,
                    "scopes": request_scopes,
                    "state": oauth_state.state,
                },
            )

            return OAuthStartResponse(
                provider=provider,
                authorization_url=authorization_url,
                state=oauth_state.state,
                expires_at=oauth_state.expires_at,
                requested_scopes=request_scopes,
            )

        except Exception as e:
            self.logger.error(
                "Failed to start OAuth flow",
                user_id=user_id,
                provider=provider,
                redirect_uri=redirect_uri,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,  # This will include the full traceback
            )
            if isinstance(e, (NotFoundException, SimpleValidationException)):
                raise
            raise IntegrationException(f"Failed to start OAuth flow: {str(e)}")

    async def complete_oauth_flow(
        self,
        user_id: str,
        provider: IntegrationProvider,
        authorization_code: str,
        state: str,
    ) -> OAuthCallbackResponse:
        """
        Complete OAuth authorization flow and create/update integration.

        Args:
            user_id: User identifier
            provider: OAuth provider
            authorization_code: Authorization code from provider
            state: OAuth state parameter

        Returns:
            OAuthCallbackResponse with integration details

        Raises:
            NotFoundException: If user not found
            SimpleValidationException: If invalid state or authorization code
            IntegrationException: If OAuth flow fails
        """
        try:
            # Verify user exists
            async_session = get_async_session()
            async with async_session() as session:
                result = await session.execute(
                    select(User).where(User.external_auth_id == user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    raise NotFoundException(f"User not found: {user_id}")

            # Validate OAuth state
            oauth_state = self.oauth_config.validate_state(state, user_id, provider)
            if not oauth_state:
                raise SimpleValidationException("Invalid or expired OAuth state")

            # Exchange authorization code for tokens
            tokens = await self.oauth_config.exchange_code_for_tokens(
                provider=provider,
                authorization_code=authorization_code,
                oauth_state=oauth_state,
            )

            # Get user info from provider
            user_info = await self.oauth_config.get_user_info(
                provider=provider,
                access_token=tokens["access_token"],
            )

            # Create or update integration
            integration = await self._create_or_update_integration(
                user=user,
                provider=provider,
                tokens=tokens,
                user_info=user_info,
            )

            # Store encrypted tokens
            if integration.id is None:
                raise IntegrationException("Integration was not properly saved")
            await self._store_encrypted_tokens(integration.id, tokens)

            # Update integration status
            async with async_session() as session:
                integration.status = IntegrationStatus.ACTIVE
                integration.last_sync_at = datetime.now(timezone.utc)
                integration.error_message = None
                integration.updated_at = datetime.now(timezone.utc)
                session.add(integration)
                await session.commit()

            # Clean up OAuth state
            self.oauth_config.remove_state(oauth_state.state)

            # Log successful OAuth completion
            await get_audit_logger().log_user_action(
                user_id=user_id,
                action="oauth_flow_completed",
                resource_type="integration",
                details={
                    "provider": provider.value,
                    "integration_id": integration.id,
                    "scopes": (
                        list(tokens.get("scope", "").split())
                        if tokens.get("scope")
                        else []
                    ),
                    "provider_user_id": user_info.get("id"),
                },
            )

            return OAuthCallbackResponse(
                success=True,
                integration_id=integration.id,
                provider=provider,
                status=IntegrationStatus.ACTIVE,
                scopes=(
                    list(tokens.get("scope", "").split()) if tokens.get("scope") else []
                ),
                external_user_info=user_info,
                error=None,
            )

        except Exception as e:
            self.logger.error(
                "Failed to complete OAuth flow",
                user_id=user_id,
                provider=provider,
                authorization_code=(
                    authorization_code[:10] + "..." if authorization_code else None
                ),
                state=state,
                error=str(e),
            )

            # Log failed OAuth completion
            await get_audit_logger().log_security_event(
                user_id=user_id,
                action="oauth_flow_failed",
                severity="medium",
                details={
                    "provider": provider.value,
                    "error": str(e),
                    "state": state,
                },
            )

            if isinstance(e, (NotFoundException, SimpleValidationException)):
                raise

            return OAuthCallbackResponse(
                success=False,
                integration_id=None,
                provider=provider,
                status=IntegrationStatus.ERROR,
                scopes=[],
                external_user_info=None,
                error=str(e),
            )

    async def refresh_integration_tokens(
        self,
        user_id: str,
        provider: IntegrationProvider,
        force: bool = False,
    ) -> TokenRefreshResponse:
        """
        Refresh access tokens for an integration.

        Args:
            user_id: User identifier
            provider: OAuth provider
            force: Force refresh even if token not near expiration

        Returns:
            TokenRefreshResponse with refresh status

        Raises:
            NotFoundException: If user or integration not found
            IntegrationException: If refresh fails
        """
        try:
            # Get integration
            integration = await self._get_user_integration(user_id, provider)

            # Get encrypted tokens
            async_session = get_async_session()
            async with async_session() as session:
                token_result = await session.execute(
                    select(EncryptedToken).where(
                        EncryptedToken.integration_id == integration.id
                    )
                )
                token_record = token_result.scalar_one_or_none()
            if not token_record:
                raise IntegrationException("No tokens found for integration")

            # Decrypt tokens
            access_token = None
            refresh_token = None

            # Get access token
            access_token_result = await session.execute(
                select(EncryptedToken).where(
                    EncryptedToken.integration_id == integration.id,
                    EncryptedToken.token_type == TokenType.ACCESS,
                )
            )
            access_token_record = access_token_result.scalar_one_or_none()
            if access_token_record:
                access_token = self.token_encryption.decrypt_token(
                    encrypted_token=access_token_record.encrypted_value,
                    user_id=user_id,
                )

            # Get refresh token
            refresh_token_result = await session.execute(
                select(EncryptedToken).where(
                    EncryptedToken.integration_id == integration.id,
                    EncryptedToken.token_type == TokenType.REFRESH,
                )
            )
            refresh_token_record = refresh_token_result.scalar_one_or_none()
            if refresh_token_record:
                refresh_token = self.token_encryption.decrypt_token(
                    encrypted_token=refresh_token_record.encrypted_value,
                    user_id=user_id,
                )

            if not access_token:
                raise IntegrationException("No access token found for integration")

            tokens = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": (
                    access_token_record.expires_at.isoformat()
                    if access_token_record and access_token_record.expires_at
                    else None
                ),
            }

            # Check if refresh is needed
            if not force and tokens.get("expires_at"):
                expires_at = datetime.fromisoformat(tokens["expires_at"])
                # Ensure expires_at is timezone-aware
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                # Refresh if expires within 5 minutes
                if expires_at > datetime.now(timezone.utc) + timedelta(minutes=5):
                    return TokenRefreshResponse(
                        success=True,
                        integration_id=integration.id,
                        provider=provider,
                        token_expires_at=expires_at,
                        refreshed_at=datetime.now(timezone.utc),
                        error=None,
                    )

            # Refresh tokens
            new_tokens = await self.oauth_config.refresh_access_token(
                provider=provider,
                refresh_token=tokens.get("refresh_token"),
            )

            # Store new encrypted tokens
            if integration.id is None:
                raise IntegrationException("Integration was not properly saved")
            await self._store_encrypted_tokens(integration.id, new_tokens)

            # Update integration
            async with async_session() as session:
                await session.execute(
                    select(Integration).where(Integration.id == integration.id)
                )
                integration.status = IntegrationStatus.ACTIVE
                integration.last_sync_at = datetime.now(timezone.utc)
                integration.error_message = None
                integration.updated_at = datetime.now(timezone.utc)
                session.add(integration)
                await session.commit()

            # Log token refresh
            await get_audit_logger().log_user_action(
                user_id=user_id,
                action="tokens_refreshed",
                resource_type="integration",
                details={
                    "provider": provider.value,
                    "integration_id": integration.id,
                    "forced": force,
                },
            )

            new_expires_at: Optional[datetime] = None
            if new_tokens.get("expires_in"):
                new_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=new_tokens["expires_in"]
                )

            return TokenRefreshResponse(
                success=True,
                integration_id=integration.id,
                provider=provider,
                token_expires_at=new_expires_at,
                refreshed_at=datetime.now(timezone.utc),
                error=None,
            )

        except Exception as e:
            self.logger.error(
                "Failed to refresh tokens",
                user_id=user_id,
                provider=provider,
                force=force,
                error=str(e),
            )

            # Update integration status on refresh failure
            try:
                integration = await self._get_user_integration(user_id, provider)
                async with async_session() as session:
                    integration.status = IntegrationStatus.ERROR
                    integration.error_message = f"Token refresh failed: {str(e)}"
                    integration.updated_at = datetime.now(timezone.utc)
                    session.add(integration)
                    await session.commit()
            except Exception:
                pass  # Don't fail if we can't update status

            if isinstance(e, NotFoundException):
                raise

            integration_id: Optional[int] = None
            try:
                integration = await self._get_user_integration(user_id, provider)
                integration_id = integration.id
            except Exception:
                pass

            return TokenRefreshResponse(
                success=False,
                integration_id=integration_id,
                provider=provider,
                token_expires_at=None,
                refreshed_at=datetime.now(timezone.utc),
                error=str(e),
            )

    async def disconnect_integration(
        self,
        user_id: str,
        provider: IntegrationProvider,
        revoke_tokens: bool = True,
        delete_data: bool = False,
    ) -> Dict[str, Any]:
        """
        Disconnect an integration and optionally revoke tokens.

        Args:
            user_id: User identifier
            provider: OAuth provider
            revoke_tokens: Whether to revoke tokens with provider
            delete_data: Whether to delete integration data

        Returns:
            Dictionary with disconnection results

        Raises:
            NotFoundException: If integration not found
            IntegrationException: If disconnect fails
        """
        try:
            # Get integration
            integration = await self._get_user_integration(user_id, provider)

            tokens_revoked = False
            if revoke_tokens:
                # Get and revoke tokens
                async_session = get_async_session()
                async with async_session() as session:
                    # Get access token
                    access_token_result = await session.execute(
                        select(EncryptedToken).where(
                            EncryptedToken.integration_id == integration.id,
                            EncryptedToken.token_type == TokenType.ACCESS,
                        )
                    )
                    access_token_record = access_token_result.scalar_one_or_none()

                    # Get refresh token
                    refresh_token_result = await session.execute(
                        select(EncryptedToken).where(
                            EncryptedToken.integration_id == integration.id,
                            EncryptedToken.token_type == TokenType.REFRESH,
                        )
                    )
                    refresh_token_record = refresh_token_result.scalar_one_or_none()

                    # Check if we have any tokens to revoke
                    if not access_token_record and not refresh_token_record:
                        raise IntegrationException(
                            "No tokens found to revoke. You can disconnect without token revocation."
                        )

                    # Track actual revocation success
                    access_token_revoked = False
                    refresh_token_revoked = False
                    revocation_errors = []

                    # Revoke access token
                    if access_token_record:
                        try:
                            access_token = self.token_encryption.decrypt_token(
                                encrypted_token=access_token_record.encrypted_value,
                                user_id=user_id,
                            )
                            access_token_revoked = await self.oauth_config.revoke_token(
                                provider=provider,
                                token=access_token,
                                token_type="access_token",
                            )
                            if not access_token_revoked:
                                revocation_errors.append(
                                    "Access token revocation failed"
                                )
                        except Exception as e:
                            revocation_errors.append(
                                f"Access token revocation error: {str(e)}"
                            )

                    # Revoke refresh token if available
                    if refresh_token_record:
                        try:
                            refresh_token = self.token_encryption.decrypt_token(
                                encrypted_token=refresh_token_record.encrypted_value,
                                user_id=user_id,
                            )
                            refresh_token_revoked = (
                                await self.oauth_config.revoke_token(
                                    provider=provider,
                                    token=refresh_token,
                                    token_type="refresh_token",
                                )
                            )
                            if not refresh_token_revoked:
                                revocation_errors.append(
                                    "Refresh token revocation failed"
                                )
                        except Exception as e:
                            revocation_errors.append(
                                f"Refresh token revocation error: {str(e)}"
                            )

                    # Check if any tokens were successfully revoked
                    tokens_revoked = access_token_revoked or refresh_token_revoked

                    # If revocation was requested but completely failed, raise an error
                    if not tokens_revoked and revocation_errors:
                        error_message = "; ".join(revocation_errors)
                        raise IntegrationException(
                            f"Token revocation failed: {error_message}. "
                            "You can retry without token revocation if needed."
                        )

            # Delete or deactivate integration
            async_session = get_async_session()
            async with async_session() as session:
                if delete_data:
                    # Delete encrypted tokens first
                    token_result = await session.execute(
                        select(EncryptedToken).where(
                            EncryptedToken.integration_id == integration.id
                        )
                    )
                    tokens_to_delete = token_result.scalars().all()
                    for token in tokens_to_delete:
                        await session.delete(token)
                    # Delete integration
                    await session.delete(integration)
                    await session.commit()
                else:
                    # Just mark as inactive
                    integration.status = IntegrationStatus.INACTIVE
                    integration.updated_at = datetime.now(timezone.utc)
                    session.add(integration)
                    await session.commit()

            # Log disconnection
            await get_audit_logger().log_user_action(
                user_id=user_id,
                action="integration_disconnected",
                resource_type="integration",
                details={
                    "provider": provider.value,
                    "integration_id": integration.id,
                    "tokens_revoked": tokens_revoked,
                    "data_deleted": delete_data,
                },
            )

            return {
                "success": True,
                "integration_id": integration.id,
                "provider": provider,
                "tokens_revoked": tokens_revoked,
                "data_deleted": delete_data,
                "disconnected_at": datetime.now(timezone.utc),
                "error": None,
            }

        except Exception as e:
            self.logger.error(
                "Failed to disconnect integration",
                user_id=user_id,
                provider=provider,
                revoke_tokens=revoke_tokens,
                delete_data=delete_data,
                error=str(e),
            )
            if isinstance(e, NotFoundException):
                raise
            raise IntegrationException(f"Failed to disconnect integration: {str(e)}")

    async def check_integration_health(
        self,
        user_id: str,
        provider: IntegrationProvider,
    ) -> IntegrationHealthResponse:
        """
        Check the health status of an integration.

        Args:
            user_id: User identifier
            provider: OAuth provider

        Returns:
            IntegrationHealthResponse with health details

        Raises:
            NotFoundException: If integration not found
        """
        try:
            # Get integration
            integration = await self._get_user_integration(user_id, provider)

            issues = []
            recommendations = []
            healthy = True

            # Check integration status
            if integration.status == IntegrationStatus.ERROR:
                healthy = False
                issues.append("Integration is in error state")
                if integration.error_message:
                    issues.append(f"Last error: {integration.error_message}")
                recommendations.append("Try refreshing tokens or reconnecting")

            elif integration.status == IntegrationStatus.INACTIVE:
                healthy = False
                issues.append("Integration is inactive")
                recommendations.append("Reconnect the integration")

            elif integration.status == IntegrationStatus.PENDING:
                healthy = False
                issues.append("Integration setup is incomplete")
                recommendations.append("Complete the OAuth flow")

            # Check token validity
            if integration.status == IntegrationStatus.ACTIVE:
                async_session = get_async_session()
                async with async_session() as session:
                    token_result = await session.execute(
                        select(EncryptedToken).where(
                            EncryptedToken.integration_id == integration.id
                        )
                    )
                    token_record = token_result.scalar_one_or_none()
                if not token_record:
                    healthy = False
                    issues.append("No tokens found")
                    recommendations.append("Reconnect the integration")
                else:
                    try:
                        # Get access token to check expiration
                        access_token_result = await session.execute(
                            select(EncryptedToken).where(
                                EncryptedToken.integration_id == integration.id,
                                EncryptedToken.token_type == TokenType.ACCESS,
                            )
                        )
                        access_token_record = access_token_result.scalar_one_or_none()

                        # Check token expiration
                        if access_token_record and access_token_record.expires_at:
                            # Ensure expires_at is timezone-aware for comparison
                            expires_at = access_token_record.expires_at
                            if expires_at.tzinfo is None:
                                expires_at = expires_at.replace(tzinfo=timezone.utc)

                            now = datetime.now(timezone.utc)
                            if expires_at <= now:
                                issues.append("Access token has expired")
                                # Check if refresh token exists
                                refresh_token_result = await session.execute(
                                    select(EncryptedToken).where(
                                        EncryptedToken.integration_id == integration.id,
                                        EncryptedToken.token_type == TokenType.REFRESH,
                                    )
                                )
                                refresh_token_record = (
                                    refresh_token_result.scalar_one_or_none()
                                )
                                if refresh_token_record:
                                    recommendations.append("Refresh the access token")
                                else:
                                    healthy = False
                                    recommendations.append("Reconnect the integration")
                            elif expires_at <= now + timedelta(hours=1):
                                issues.append("Access token expires soon")
                                recommendations.append("Consider refreshing the token")

                    except Exception as e:
                        healthy = False
                        issues.append(f"Token decryption failed: {str(e)}")
                        recommendations.append("Reconnect the integration")

            # Check last sync time
            if integration.last_sync_at:
                time_since_sync = datetime.now(timezone.utc) - integration.last_sync_at
                if time_since_sync > timedelta(days=7):
                    issues.append("No recent synchronization activity")
                    recommendations.append("Verify integration is working properly")

            return IntegrationHealthResponse(
                integration_id=integration.id,
                provider=provider,
                status=integration.status,
                healthy=healthy,
                last_check_at=datetime.now(timezone.utc),
                issues=issues,
                recommendations=recommendations,
            )

        except Exception as e:
            self.logger.error(
                "Failed to check integration health",
                user_id=user_id,
                provider=provider,
                error=str(e),
            )
            if isinstance(e, NotFoundException):
                raise
            raise IntegrationException(f"Failed to check integration health: {str(e)}")

    async def get_integration_statistics(
        self, user_id: str
    ) -> IntegrationStatsResponse:
        """
        Get statistics for all user integrations.

        Args:
            user_id: User identifier

        Returns:
            IntegrationStatsResponse with statistics

        Raises:
            NotFoundException: If user not found
        """
        try:
            # Verify user exists and get integrations
            async_session = get_async_session()
            async with async_session() as session:
                user_result = await session.execute(
                    select(User).where(User.external_auth_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    raise NotFoundException(f"User not found: {user_id}")

                # Get all integrations for user
                integrations_result = await session.execute(
                    select(Integration).where(Integration.user_id == user.id)
                )
                integrations = list(integrations_result.scalars().all())

            # Calculate basic stats
            total = len(integrations)
            by_status: Dict[str, int] = {}
            by_provider: Dict[str, int] = {}
            recent_errors = []

            for integration in integrations:
                # Count by status
                status_key = integration.status.value
                by_status[status_key] = by_status.get(status_key, 0) + 1

                # Count by provider
                provider_key = integration.provider.value
                by_provider[provider_key] = by_provider.get(provider_key, 0) + 1

                # Collect recent errors
                if (
                    integration.status == IntegrationStatus.ERROR
                    and integration.error_message
                ):
                    recent_errors.append(
                        {
                            "integration_id": integration.id,
                            "provider": integration.provider.value,
                            "error": integration.error_message,
                            "timestamp": integration.updated_at.isoformat(),
                        }
                    )

            # Sort recent errors by timestamp (most recent first)
            recent_errors = sorted(
                recent_errors, key=lambda x: x["timestamp"], reverse=True
            )[
                :10
            ]  # Keep only 10 most recent

            # Calculate sync stats
            sync_stats = {}
            if integrations:
                last_sync_times = [
                    i.last_sync_at for i in integrations if i.last_sync_at
                ]
                if last_sync_times:
                    sync_stats["last_sync"] = max(last_sync_times).isoformat()
                    sync_stats["total_synced"] = len(last_sync_times)

            return IntegrationStatsResponse(
                total_integrations=total,
                active_integrations=by_status.get("active", 0),
                failed_integrations=by_status.get("error", 0),
                pending_integrations=by_status.get("pending", 0),
                by_provider=by_provider,
                by_status=by_status,
                recent_errors=recent_errors,
                sync_stats=sync_stats,
            )

        except Exception as e:
            self.logger.error(
                "Failed to get integration statistics",
                user_id=user_id,
                error=str(e),
            )
            if isinstance(e, NotFoundException):
                raise
            raise IntegrationException(f"Failed to get statistics: {str(e)}")

    # Private helper methods

    async def _get_user_integration(
        self,
        user_id: str,
        provider: IntegrationProvider,
    ) -> Integration:
        """Get integration for user and provider."""
        async_session = get_async_session()
        async with async_session() as session:
            # First get the user
            user_result = await session.execute(
                select(User).where(User.external_auth_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Then get the integration
            integration_result = await session.execute(
                select(Integration).where(
                    Integration.user_id == user.id, Integration.provider == provider
                )
            )
            integration = integration_result.scalar_one_or_none()

        if not integration:
            raise NotFoundException(f"Integration not found: {provider.value}")
        return integration

    async def _get_token_metadata(self, integration_id: int) -> Dict[str, Any]:
        """Get token metadata without decrypting actual tokens."""
        async_session = get_async_session()
        async with async_session() as session:
            # Get access token record
            access_token_result = await session.execute(
                select(EncryptedToken).where(
                    EncryptedToken.integration_id == integration_id,
                    EncryptedToken.token_type == TokenType.ACCESS,
                )
            )
            access_token_record = access_token_result.scalar_one_or_none()

            # Get refresh token record
            refresh_token_result = await session.execute(
                select(EncryptedToken).where(
                    EncryptedToken.integration_id == integration_id,
                    EncryptedToken.token_type == TokenType.REFRESH,
                )
            )
            refresh_token_record = refresh_token_result.scalar_one_or_none()

        return {
            "has_access_token": access_token_record is not None,
            "has_refresh_token": refresh_token_record is not None,
            "expires_at": (
                access_token_record.expires_at if access_token_record else None
            ),
            "created_at": (
                access_token_record.created_at if access_token_record else None
            ),
        }

    async def _get_error_count(self, integration_id: int) -> int:
        """Get consecutive error count for integration from audit logs."""
        try:
            # This would typically query audit logs for consecutive errors
            # For now, return a simple count based on status
            async_session = get_async_session()
            async with async_session() as session:
                integration_result = await session.execute(
                    select(Integration).where(Integration.id == integration_id)
                )
                integration = integration_result.scalar_one_or_none()
                return (
                    1
                    if integration and integration.status == IntegrationStatus.ERROR
                    else 0
                )
        except Exception:
            return 0

    async def _create_or_update_integration(
        self,
        user: User,
        provider: IntegrationProvider,
        tokens: Dict[str, Any],
        user_info: Dict[str, Any],
    ) -> Integration:
        """Create or update integration record."""
        async_session = get_async_session()
        async with async_session() as session:
            # Check if integration already exists
            result = await session.execute(
                select(Integration).where(
                    Integration.user_id == user.id, Integration.provider == provider
                )
            )
            integration = result.scalar_one_or_none()

            scopes_dict = {}
            if tokens.get("scope"):
                # Convert scope string to dictionary
                scopes_dict = {scope: True for scope in tokens["scope"].split()}

            integration_data = {
                "provider_user_id": user_info.get("id"),
                "provider_email": user_info.get("email"),
                "scopes": scopes_dict,
                "provider_metadata": user_info,
                "last_sync_at": datetime.now(timezone.utc),
                "error_message": None,
                "updated_at": datetime.now(timezone.utc),
            }

            if integration:
                # Update existing integration
                for key, value in integration_data.items():
                    setattr(integration, key, value)
                await session.commit()
                await session.refresh(integration)
            else:
                # Create new integration
                integration = Integration(
                    user_id=user.id,
                    provider=provider,
                    status=IntegrationStatus.PENDING,
                    **integration_data,
                )
                session.add(integration)
                await session.commit()
                await session.refresh(integration)

        # Log the integration creation
        await get_audit_logger().log_user_action(
            user_id=user.external_auth_id,
            action="integration_created",
            resource_type="integration",
            resource_id=str(integration.id),
            details={
                "provider": provider.value,
                "scopes": scopes_dict,
                "external_user_id": user_info.get("id"),
            },
        )

        return integration

    async def _store_encrypted_tokens(
        self,
        integration_id: int,
        tokens: Dict[str, Any],
    ) -> None:
        """Store encrypted tokens for integration."""
        async_session = get_async_session()
        async with async_session() as session:
            # Get integration to get user_id
            result = await session.execute(
                select(Integration).where(Integration.id == integration_id)
            )
            integration = result.scalar_one()

            # Get user to get external auth ID
            user_result = await session.execute(
                select(User).where(User.id == integration.user_id)
            )
            user = user_result.scalar_one()
            user_id = user.external_auth_id

            # Encrypt tokens
            encrypted_access = self.token_encryption.encrypt_token(
                token=tokens.get("access_token", ""),
                user_id=user_id,
            )

            encrypted_refresh = None
            if tokens.get("refresh_token"):
                encrypted_refresh = self.token_encryption.encrypt_token(
                    token=tokens.get("refresh_token", ""),
                    user_id=user_id,
                )

            # Calculate expiration time
            expires_at = None
            if tokens.get("expires_in"):
                expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=tokens["expires_in"]
                )

            # Store access token
            access_token_result = await session.execute(
                select(EncryptedToken).where(
                    EncryptedToken.integration_id == integration_id,
                    EncryptedToken.token_type == TokenType.ACCESS,
                )
            )
            access_token_record = access_token_result.scalar_one_or_none()

            if access_token_record:
                access_token_record.encrypted_value = encrypted_access
                access_token_record.expires_at = expires_at
                access_token_record.updated_at = datetime.now(timezone.utc)
                await session.commit()
            else:
                new_access_token = EncryptedToken(
                    user_id=integration.user_id,
                    integration_id=integration_id,
                    token_type=TokenType.ACCESS,
                    encrypted_value=encrypted_access,
                    expires_at=expires_at,
                )
                session.add(new_access_token)
                await session.commit()

            # Store refresh token if provided
            if encrypted_refresh:
                refresh_token_result = await session.execute(
                    select(EncryptedToken).where(
                        EncryptedToken.integration_id == integration_id,
                        EncryptedToken.token_type == TokenType.REFRESH,
                    )
                )
                refresh_token_record = refresh_token_result.scalar_one_or_none()

                if refresh_token_record:
                    refresh_token_record.encrypted_value = encrypted_refresh
                    refresh_token_record.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                else:
                    new_refresh_token = EncryptedToken(
                        user_id=integration.user_id,
                        integration_id=integration_id,
                        token_type=TokenType.REFRESH,
                        encrypted_value=encrypted_refresh,
                        expires_at=None,  # Refresh tokens usually don't expire
                    )
                    session.add(new_refresh_token)
                    await session.commit()


def get_integration_service() -> IntegrationService:
    """Get integration service instance (lazy singleton)."""
    return IntegrationService()
