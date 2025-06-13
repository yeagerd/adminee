"""
User Management Service - Integrations Package

This package contains OAuth integration configurations and utilities
for connecting to external providers like Google, Microsoft, and Slack.
"""

from .oauth_config import (
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
    "PKCEChallengeMethod",
    "get_oauth_config",
    "reset_oauth_config",
]
