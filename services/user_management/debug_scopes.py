#!/usr/bin/env python3
"""
Debug script to show Microsoft OAuth scope configuration.
"""

import sys
from pathlib import Path

# Now import after path modification
from services.user_management.integrations.oauth_config import (  # noqa: E402
    OAuthConfig,
    reset_oauth_config,
)
from services.user_management.models.integration import IntegrationProvider  # noqa: E402
from services.user_management.settings import Settings  # noqa: E402


def debug_microsoft_scopes():
    """Debug Microsoft OAuth scope configuration."""
    print("🔍 Debugging Microsoft OAuth scope configuration...")

    try:
        # Force reset to ensure we get fresh config
        reset_oauth_config()

        # Initialize OAuth config
        settings = Settings()
        oauth_config = OAuthConfig(settings)

        # Get Microsoft provider config
        provider_config = oauth_config.get_provider_config(
            IntegrationProvider.MICROSOFT
        )

        if not provider_config:
            print("❌ Microsoft provider not available")
            return False

        print("✅ Microsoft provider configuration:")
        print(f"   - Provider: {provider_config.provider}")
        print(f"   - Name: {provider_config.name}")
        print(f"   - Client ID configured: {bool(provider_config.client_id)}")
        print(f"   - Default scopes: {provider_config.default_scopes}")

        print("\n📋 Available scopes:")
        for i, scope in enumerate(provider_config.scopes, 1):
            print(f"   {i}. {scope.name}")
            print(f"      Description: {scope.description}")
            print(f"      Required: {scope.required}")
            print(f"      Sensitive: {scope.sensitive}")

        print("\n🧪 Testing scope validation...")

        # Test default scopes
        default_scopes = provider_config.default_scopes
        valid_scopes, invalid_scopes = provider_config.validate_scopes(default_scopes)

        print(f"   Default scopes: {default_scopes}")
        print(f"   Valid: {valid_scopes}")
        print(f"   Invalid: {invalid_scopes}")

        if invalid_scopes:
            print("❌ PROBLEM: Default scopes are invalid!")
            print(f"   Invalid scopes: {invalid_scopes}")
            print(
                f"   Available scope names: {[s.name for s in provider_config.scopes]}"
            )
            return False
        else:
            print("✅ Default scopes validation passed!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = debug_microsoft_scopes()
    if success:
        print("\n🎉 Microsoft OAuth scope configuration is correct!")
    else:
        print("\n💥 There are issues with the Microsoft OAuth scope configuration.")

    sys.exit(0 if success else 1)
