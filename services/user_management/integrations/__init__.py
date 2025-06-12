"""
Integrations package for User Management Service.

Provides OAuth provider configurations and integration management
for connecting to external services like Google, Microsoft, and others.
"""

from services.user_management.integrations.oauth_config import (
    OAuthConfig,
    OAuthProviderConfig,
    OAuthScope,
    OAuthState,
    PKCEChallenge,
    PKCEChallengeMethod,
    get_oauth_config,
    reset_oauth_config,
)

__all__ = [
    "OAuthConfig",
    "OAuthProviderConfig",
    "OAuthScope",
    "OAuthState",
    "PKCEChallenge",
    "get_oauth_config",
    "reset_oauth_config",
]
