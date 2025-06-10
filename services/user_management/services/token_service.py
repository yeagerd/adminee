"""
Token service for User Management Service.

Provides secure token storage, retrieval, and lifecycle management for
internal service-to-service communication with automatic refresh and validation.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import httpx
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
    TokenRevocationResponse,
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
            user = await User.objects.get_or_none(external_auth_id=user_id)
            if not user:
                raise NotFoundException(f"User not found: {user_id}")

            # Get all user integrations
            integrations = await Integration.objects.filter(
                user__external_auth_id=user_id
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
            user__external_auth_id=user_id, provider=provider
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

    async def revoke_tokens(
        self,
        user_id: str,
        provider: IntegrationProvider,
        reason: str = "user_request",
    ) -> TokenRevocationResponse:
        """
        Revoke tokens with provider and clean up locally.

        Args:
            user_id: User identifier
            provider: OAuth provider
            reason: Reason for revocation (for audit trail)

        Returns:
            TokenRevocationResponse with revocation status
        """
        try:
            # Get user integration
            integration = await self._get_user_integration(user_id, provider)

            # Get tokens to revoke
            access_token_record = await EncryptedToken.objects.get_or_none(
                integration=integration, token_type=TokenType.ACCESS
            )
            refresh_token_record = await EncryptedToken.objects.get_or_none(
                integration=integration, token_type=TokenType.REFRESH
            )

            if not access_token_record and not refresh_token_record:
                return TokenRevocationResponse(
                    success=True,  # No tokens to revoke is considered success
                    provider=provider,
                    user_id=user_id,
                    integration_id=integration.id,
                    revoked_at=datetime.now(timezone.utc),
                    reason=reason,
                    error="No tokens found to revoke",
                )

            revocation_results = []

            # Revoke access token with provider
            if access_token_record:
                access_token = self.token_encryption.decrypt_token(
                    encrypted_token=access_token_record.encrypted_value,
                    user_id=user_id,
                )

                provider_result = await self._revoke_with_provider(
                    provider, access_token, "access_token"
                )
                revocation_results.append(provider_result)

            # Revoke refresh token with provider
            if refresh_token_record:
                refresh_token = self.token_encryption.decrypt_token(
                    encrypted_token=refresh_token_record.encrypted_value,
                    user_id=user_id,
                )

                provider_result = await self._revoke_with_provider(
                    provider, refresh_token, "refresh_token"
                )
                revocation_results.append(provider_result)

            # Clean up local token storage
            if access_token_record:
                await access_token_record.delete()
            if refresh_token_record:
                await refresh_token_record.delete()

            # Update integration status
            await integration.update(
                status=IntegrationStatus.ERROR,  # Use ERROR instead of DISCONNECTED
                last_error=None,
                error_count=0,
                updated_at=datetime.now(timezone.utc),
            )

            # Determine overall success
            overall_success = any(
                result.get("success", False) for result in revocation_results
            )
            errors = [str(r.get("error")) for r in revocation_results if r.get("error")]

            # Log audit event
            await audit_logger.log_user_action(
                user_id=user_id,
                action="tokens_revoked",
                resource_type="token",
                details={
                    "provider": provider.value,
                    "integration_id": integration.id,
                    "reason": reason,
                    "success": overall_success,
                    "provider_results": revocation_results,
                },
            )

            self.logger.info(
                "Token revocation completed",
                user_id=user_id,
                provider=provider.value,
                integration_id=integration.id,
                success=overall_success,
                reason=reason,
            )

            return TokenRevocationResponse(
                success=overall_success,
                provider=provider,
                user_id=user_id,
                integration_id=integration.id,
                revoked_at=datetime.now(timezone.utc),
                reason=reason,
                error="; ".join(errors) if errors else None,
                provider_response={"results": revocation_results},
            )

        except Exception as e:
            self.logger.error(
                "Failed to revoke tokens",
                user_id=user_id,
                provider=provider.value,
                reason=reason,
                error=str(e),
            )
            return TokenRevocationResponse(
                success=False,
                provider=provider,
                user_id=user_id,
                reason=reason,
                error=f"Token revocation failed: {str(e)}",
            )

    async def revoke_all_user_tokens(
        self, user_id: str, reason: str = "account_deletion"
    ) -> List[TokenRevocationResponse]:
        """
        Revoke all tokens for a user (e.g., account deletion).

        Args:
            user_id: User identifier
            reason: Reason for bulk revocation

        Returns:
            List of TokenRevocationResponse for each provider
        """
        try:
            # Get all user integrations
            integrations = await Integration.objects.filter(
                user__external_auth_id=user_id
            ).all()

            if not integrations:
                self.logger.info(
                    "No integrations found for user",
                    user_id=user_id,
                    reason=reason,
                )
                return []

            revocation_responses = []

            # Revoke tokens for each provider
            for integration in integrations:
                if integration.status == IntegrationStatus.ACTIVE:
                    response = await self.revoke_tokens(
                        user_id=user_id,
                        provider=integration.provider,
                        reason=reason,
                    )
                    revocation_responses.append(response)

            await audit_logger.log_user_action(
                user_id=user_id,
                action="all_tokens_revoked",
                resource_type="token",
                details={
                    "reason": reason,
                    "integrations_count": len(integrations),
                    "revoked_count": len(revocation_responses),
                    "results": [r.dict() for r in revocation_responses],
                },
            )

            self.logger.info(
                "Bulk token revocation completed",
                user_id=user_id,
                reason=reason,
                total_integrations=len(integrations),
                revoked_count=len(revocation_responses),
            )

            return revocation_responses

        except Exception as e:
            self.logger.error(
                "Failed to revoke all user tokens",
                user_id=user_id,
                reason=reason,
                error=str(e),
            )
            # Return error response for unknown integration
            return [
                TokenRevocationResponse(
                    success=False,
                    provider=IntegrationProvider.GOOGLE,  # Default for error case
                    user_id=user_id,
                    reason=reason,
                    error=f"Bulk revocation failed: {str(e)}",
                )
            ]

    async def emergency_revoke_tokens(
        self, criteria: Dict, reason: str = "security_incident"
    ) -> int:
        """
        Bulk revoke tokens matching criteria (e.g., security incident).

        Args:
            criteria: Dictionary with filtering criteria
            reason: Reason for emergency revocation

        Returns:
            Number of integrations processed
        """
        try:
            # Build query based on criteria
            query = Integration.objects.filter(status=IntegrationStatus.ACTIVE)

            if "provider" in criteria:
                query = query.filter(provider=criteria["provider"])
            if "user_ids" in criteria:
                query = query.filter(user__external_auth_id__in=criteria["user_ids"])
            if "created_after" in criteria:
                query = query.filter(created_at__gte=criteria["created_after"])
            if "last_sync_before" in criteria:
                query = query.filter(last_sync_at__lte=criteria["last_sync_before"])

            integrations = await query.all()

            if not integrations:
                self.logger.warning(
                    "No integrations matched emergency revocation criteria",
                    criteria=criteria,
                    reason=reason,
                )
                return 0

            revocation_count = 0

            # Revoke tokens for matching integrations
            for integration in integrations:
                try:
                    response = await self.revoke_tokens(
                        user_id=integration.user.external_auth_id,
                        provider=integration.provider,
                        reason=reason,
                    )
                    if response.success:
                        revocation_count += 1
                except Exception as e:
                    self.logger.error(
                        "Failed to revoke tokens for integration",
                        integration_id=integration.id,
                        user_id=integration.user.external_auth_id,
                        provider=integration.provider.value,
                        error=str(e),
                    )

            await audit_logger.log_system_action(
                action="emergency_token_revocation",
                resource_type="token",
                details={
                    "criteria": criteria,
                    "reason": reason,
                    "matched_integrations": len(integrations),
                    "successful_revocations": revocation_count,
                },
            )

            self.logger.warning(
                "Emergency token revocation completed",
                criteria=criteria,
                reason=reason,
                matched_count=len(integrations),
                revoked_count=revocation_count,
            )

            return revocation_count

        except Exception as e:
            self.logger.error(
                "Emergency token revocation failed",
                criteria=criteria,
                reason=reason,
                error=str(e),
            )
            return 0

    async def _revoke_with_provider(
        self, provider: IntegrationProvider, token: str, token_type: str
    ) -> Dict:
        """
        Revoke token with OAuth provider.

        Args:
            provider: OAuth provider
            token: Token to revoke
            token_type: Type of token (access_token or refresh_token)

        Returns:
            Dictionary with revocation result
        """
        try:
            if provider == IntegrationProvider.GOOGLE:
                return await self._revoke_google_token(token)
            elif provider == IntegrationProvider.MICROSOFT:
                return await self._revoke_microsoft_token(token)
            else:
                return {
                    "success": False,
                    "error": f"Token revocation not implemented for {provider.value}",
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Provider revocation failed: {str(e)}",
                "provider": provider.value,
                "token_type": token_type,
            }

    async def _revoke_google_token(self, token: str) -> Dict:
        """Revoke Google OAuth token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider": "google",
                        "status_code": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Google revocation failed: {response.status_code}",
                        "provider": "google",
                        "status_code": response.status_code,
                        "response_text": response.text,
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Google revocation request failed: {str(e)}",
                "provider": "google",
            }

    async def _revoke_microsoft_token(self, token: str) -> Dict:
        """Revoke Microsoft OAuth token."""
        try:
            # Microsoft uses logout endpoint for token revocation
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://login.microsoftonline.com/common/oauth2/v2.0/logout",
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,
                )

                # Microsoft logout doesn't always return success codes consistently
                # We'll consider it successful if no error response
                if response.status_code in [200, 302, 204]:
                    return {
                        "success": True,
                        "provider": "microsoft",
                        "status_code": response.status_code,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Microsoft revocation failed: {response.status_code}",
                        "provider": "microsoft",
                        "status_code": response.status_code,
                        "response_text": response.text,
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Microsoft revocation request failed: {str(e)}",
                "provider": "microsoft",
            }


# Global token service instance
token_service = TokenService()
