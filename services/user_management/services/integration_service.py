"""
Integration service for User Management Service.

Provides comprehensive OAuth integration management including provider configuration,
token handling, lifecycle management, and health monitoring.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import structlog

from ..exceptions import (
    IntegrationException,
    NotFoundException,
    SimpleValidationException,
)
from ..integrations.oauth_config import get_oauth_config
from ..models.integration import Integration, IntegrationProvider, IntegrationStatus
from ..models.token import EncryptedToken
from ..models.user import User
from ..schemas.integration import (
    IntegrationHealthResponse,
    IntegrationListResponse,
    IntegrationResponse,
    IntegrationStatsResponse,
    OAuthCallbackResponse,
    OAuthStartResponse,
    TokenRefreshResponse,
)
from ..security.encryption import TokenEncryption
from ..services.audit_service import audit_logger

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
            user = await User.objects.get_or_none(external_auth_id=user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Build query
            query = Integration.objects.select_related("user")
            query = query.filter(user__external_auth_id=user_id)

            if provider:
                query = query.filter(provider=provider)
            if status:
                query = query.filter(status=status)

            # Get integrations
            integrations = await query.all()

            # Convert to response models
            integration_responses = []
            for integration in integrations:
                token_info = {}
                if include_token_info:
                    token_info = await self._get_token_metadata(integration.id)

                integration_response = IntegrationResponse(
                    id=integration.id,
                    user_id=integration.user.external_auth_id,
                    provider=integration.provider,
                    status=integration.status,
                    scopes=(
                        list(integration.scopes.keys()) if integration.scopes else []
                    ),
                    external_user_id=integration.provider_user_id,
                    external_email=integration.provider_email,
                    external_name=(
                        integration.metadata.get("name")
                        if integration.metadata
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

            await audit_logger.log_user_action(
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
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
        state_data: Optional[Dict[str, Any]] = None,
    ) -> OAuthStartResponse:
        """
        Start OAuth authorization flow for a provider.

        Args:
            user_id: User identifier
            provider: OAuth provider
            redirect_uri: OAuth callback URL
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
            user = await User.objects.get_or_none(external_auth_id=user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Check if provider is available
            # TODO: Implement when OAuth config is ready
            # if not self.oauth_config.is_provider_available(provider):
            #     raise SimpleValidationException(f"Provider {provider.value} is not available")

            # TODO: Implement when OAuth config is ready
            request_scopes = scopes or ["email", "profile"]

            # TODO: Generate real authorization URL
            oauth_state = type(
                "OAuthState",
                (),
                {
                    "state": f"temp_state_{user_id}_{provider.value}",
                    "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
                },
            )()
            authorization_url = f"https://oauth.{provider.value}.com/authorize?state={oauth_state.state}"

            # Log the OAuth flow start
            await audit_logger.log_user_action(
                user_id=user_id,
                action="oauth_flow_started",
                resource_type="integration",
                details={
                    "provider": provider.value,
                    "redirect_uri": redirect_uri,
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
            user = await User.objects.get_or_none(external_auth_id=user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Validate OAuth state
            if not self.oauth_config.is_valid_state(state, user_id, provider):
                raise SimpleValidationException("Invalid or expired OAuth state")

            # Exchange authorization code for tokens
            tokens = await self.oauth_config.exchange_authorization_code(
                provider=provider,
                authorization_code=authorization_code,
                state=state,
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
            await self._store_encrypted_tokens(integration.id, tokens)

            # Update integration status
            await integration.update(
                status=IntegrationStatus.ACTIVE,
                last_sync_at=datetime.now(timezone.utc),
                error_message=None,
            )

            # Clean up OAuth state
            self.oauth_config.cleanup_expired_states()

            # Log successful OAuth completion
            await audit_logger.log_user_action(
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
            await audit_logger.log_security_event(
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
            token_record = await EncryptedToken.objects.get_or_none(
                integration=integration
            )
            if not token_record:
                raise IntegrationException("No tokens found for integration")

            # Decrypt tokens
            tokens = self.token_encryption.decrypt_tokens(
                user_id=user_id,
                encrypted_data=token_record.encrypted_access_token,
                refresh_data=token_record.encrypted_refresh_token,
            )

            # Check if refresh is needed
            if not force and tokens.get("expires_at"):
                expires_at = datetime.fromisoformat(tokens["expires_at"])
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
            await self._store_encrypted_tokens(integration.id, new_tokens)

            # Update integration
            await integration.update(
                status=IntegrationStatus.ACTIVE,
                last_sync_at=datetime.now(timezone.utc),
                error_message=None,
                updated_at=datetime.now(timezone.utc),
            )

            # Log token refresh
            await audit_logger.log_user_action(
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
                await integration.update(
                    status=IntegrationStatus.ERROR,
                    error_message=f"Token refresh failed: {str(e)}",
                    updated_at=datetime.now(timezone.utc),
                )
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
                try:
                    # Get and revoke tokens
                    token_record = await EncryptedToken.objects.get_or_none(
                        integration=integration
                    )
                    if token_record:
                        tokens = self.token_encryption.decrypt_tokens(
                            user_id=user_id,
                            encrypted_data=token_record.encrypted_access_token,
                            refresh_data=token_record.encrypted_refresh_token,
                        )

                        await self.oauth_config.revoke_tokens(
                            provider=provider,
                            access_token=tokens.get("access_token"),
                            refresh_token=tokens.get("refresh_token"),
                        )
                        tokens_revoked = True
                except Exception as e:
                    self.logger.warning(
                        "Failed to revoke tokens during disconnect",
                        user_id=user_id,
                        provider=provider,
                        error=str(e),
                    )

            # Delete or deactivate integration
            if delete_data:
                # Delete encrypted tokens first
                await EncryptedToken.objects.filter(integration=integration).delete()
                # Delete integration
                await integration.delete()
            else:
                # Just mark as inactive
                await integration.update(
                    status=IntegrationStatus.INACTIVE,
                    updated_at=datetime.now(timezone.utc),
                )

            # Log disconnection
            await audit_logger.log_user_action(
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
                token_record = await EncryptedToken.objects.get_or_none(
                    integration=integration
                )
                if not token_record:
                    healthy = False
                    issues.append("No tokens found")
                    recommendations.append("Reconnect the integration")
                else:
                    try:
                        tokens = self.token_encryption.decrypt_tokens(
                            user_id=user_id,
                            encrypted_data=token_record.encrypted_access_token,
                            refresh_data=token_record.encrypted_refresh_token,
                        )

                        # Check token expiration
                        if tokens.get("expires_at"):
                            expires_at = datetime.fromisoformat(tokens["expires_at"])
                            if expires_at <= datetime.now(timezone.utc):
                                issues.append("Access token has expired")
                                if tokens.get("refresh_token"):
                                    recommendations.append("Refresh the access token")
                                else:
                                    healthy = False
                                    recommendations.append("Reconnect the integration")
                            elif expires_at <= datetime.now(timezone.utc) + timedelta(
                                hours=1
                            ):
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
            # Verify user exists
            user = await User.objects.get_or_none(external_auth_id=user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Get all integrations for user
            integrations = await Integration.objects.filter(user=user).all()

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
        integration = await Integration.objects.select_related("user").get_or_none(
            user__external_auth_id=user_id,
            provider=provider,
        )
        if not integration:
            raise NotFoundException(f"Integration not found: {provider.value}")
        return integration

    async def _get_token_metadata(self, integration_id: int) -> Dict[str, Any]:
        """Get token metadata without decrypting actual tokens."""
        token_record = await EncryptedToken.objects.get_or_none(
            integration_id=integration_id
        )
        if not token_record:
            return {
                "has_access_token": False,
                "has_refresh_token": False,
                "expires_at": None,
                "created_at": None,
            }

        return {
            "has_access_token": bool(token_record.encrypted_access_token),
            "has_refresh_token": bool(token_record.encrypted_refresh_token),
            "expires_at": token_record.expires_at,
            "created_at": token_record.created_at,
        }

    async def _get_error_count(self, integration_id: int) -> int:
        """Get consecutive error count for integration from audit logs."""
        try:
            # This would typically query audit logs for consecutive errors
            # For now, return a simple count based on status
            integration = await Integration.objects.get(id=integration_id)
            return 1 if integration.status == IntegrationStatus.ERROR else 0
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
        # Check if integration already exists
        integration = await Integration.objects.get_or_none(
            user=user,
            provider=provider,
        )

        scopes_dict = {}
        if tokens.get("scope"):
            # Convert scope string to dictionary
            scopes_dict = {scope: True for scope in tokens["scope"].split()}

        integration_data = {
            "provider_user_id": user_info.get("id"),
            "provider_email": user_info.get("email"),
            "scopes": scopes_dict,
            "metadata": user_info,
            "last_sync_at": datetime.now(timezone.utc),
            "error_message": None,
            "updated_at": datetime.now(timezone.utc),
        }

        if integration:
            # Update existing integration
            await integration.update(**integration_data)
        else:
            # Create new integration
            integration = await Integration.objects.create(
                user=user,
                provider=provider,
                status=IntegrationStatus.PENDING,
                **integration_data,
            )

        # Log the integration creation
        await audit_logger.log_user_action(
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
        # Get integration to get user_id
        integration = await Integration.objects.select_related("user").get(
            id=integration_id
        )
        user_id = integration.user.external_auth_id

        # Encrypt tokens
        encrypted_access = self.token_encryption.encrypt_token(
            user_id=user_id,
            token_data=tokens.get("access_token", ""),
        )

        encrypted_refresh = None
        if tokens.get("refresh_token"):
            encrypted_refresh = self.token_encryption.encrypt_token(
                user_id=user_id,
                token_data=tokens.get("refresh_token", ""),
            )

        # Calculate expiration time
        expires_at = None
        if tokens.get("expires_in"):
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=tokens["expires_in"]
            )

        # Store or update token record
        token_record = await EncryptedToken.objects.get_or_none(
            integration_id=integration_id
        )
        if token_record:
            await token_record.update(
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                expires_at=expires_at,
                updated_at=datetime.now(timezone.utc),
            )
        else:
            await EncryptedToken.objects.create(
                integration_id=integration_id,
                encrypted_access_token=encrypted_access,
                encrypted_refresh_token=encrypted_refresh,
                expires_at=expires_at,
            )


# Global integration service instance
integration_service = IntegrationService()
