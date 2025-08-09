#!/usr/bin/env python3
"""
Utility script to fix integration status issues.

This script validates integration status based on actual token availability
and corrects any mismatches between the status and the actual token state.
"""

import asyncio
import sys
from typing import Optional

# Add the services directory to the path
sys.path.insert(0, "services")

from user.services.integration_service import get_integration_service


async def fix_integration_status(
    user_id: Optional[str] = None, provider: Optional[str] = None
) -> None:
    """
    Fix integration status based on actual token availability.

    Args:
        user_id: Optional user ID to fix specific user's integrations
        provider: Optional provider to fix specific provider's integrations
    """
    integration_service = get_integration_service()

    if not user_id:
        print("Error: user_id is required")
        return

    print(f"Fixing integrations for user: {user_id}")

    try:
        # Get user integrations - this will automatically validate and correct status
        response = await integration_service.get_user_integrations(
            user_id=user_id,
            provider=None,  # Get all providers
            include_token_info=True,
        )

        print(f"Found {response.total} integrations")

        for integration in response.integrations:
            print(f"\nIntegration {integration.id} ({integration.provider})")
            print(f"  Status: {integration.status}")
            print(f"  Has access token: {integration.has_access_token}")
            print(f"  Has refresh token: {integration.has_refresh_token}")
            if integration.last_error:
                print(f"  Error: {integration.last_error}")

        print("\n✓ Integration status validation completed")
        print(f"  Active integrations: {response.active_count}")
        print(f"  Error integrations: {response.error_count}")

    except Exception as e:
        print(f"Error: {e}")


async def main() -> None:
    """Main function to run the script."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix integration status issues")
    parser.add_argument(
        "--user-id", required=True, help="User ID to fix specific user's integrations"
    )
    parser.add_argument(
        "--provider", help="Provider to fix specific provider's integrations"
    )

    args = parser.parse_args()

    print("Integration Status Fixer")
    print("=" * 50)

    await fix_integration_status(user_id=args.user_id, provider=args.provider)


if __name__ == "__main__":
    asyncio.run(main())
