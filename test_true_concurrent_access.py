#!/usr/bin/env python3
"""
Test script to verify true concurrent access to TokenManager.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from services.office.core.token_manager import TokenManager
from services.office.core.api_client_factory import APIClientFactory


class MockTokenManager(TokenManager):
    """Mock TokenManager that tracks instance creation and usage."""
    
    def __init__(self):
        super().__init__()
        self._instance_id = str(uuid.uuid4())[:8]
        print(f"TokenManager instance created: {self._instance_id}")
    
    async def get_user_token(self, user_id: str, provider: str, scopes: list) -> None:
        # Simulate some delay to make race conditions more likely
        await asyncio.sleep(0.1)
        print(f"TokenManager instance {self._instance_id}: Requesting token for user {user_id}, provider {provider}")
        return None


async def test_true_concurrent_access():
    """Test that truly concurrent access to TokenManager doesn't cause race conditions."""
    
    print("Testing TRUE concurrent TokenManager access...")
    print("=" * 60)
    
    # Create API client factory
    factory = APIClientFactory()
    
    # Mock the settings
    with patch('services.office.core.api_client_factory.get_settings') as mock_settings:
        mock_settings.return_value.DEMO_MODE = False
        
        # Mock the token manager creation
        with patch('services.office.core.api_client_factory.TokenManager', MockTokenManager):
            
            # Create multiple concurrent tasks that start at the same time
            async def create_client_task(task_id: int):
                print(f"Task {task_id}: Starting create_client call")
                try:
                    # All tasks start their async context managers at roughly the same time
                    await factory.create_client(f"test-user-{task_id}", "microsoft")
                    print(f"Task {task_id}: create_client completed successfully")
                except Exception as e:
                    print(f"Task {task_id}: create_client failed with {e}")
            
            # Start all tasks simultaneously
            tasks = []
            for i in range(3):
                task = asyncio.create_task(create_client_task(i))
                tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check for any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Task {i} failed with exception: {result}")
    
    print("=" * 60)
    print("Test completed. Check logs for proper ref counting and no race conditions.")


async def main():
    """Run the concurrent test."""
    await test_true_concurrent_access()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("✅ True concurrent access should show proper ref counting")
    print("✅ No 'client already closed' errors should occur")
    print("✅ All tasks should complete successfully")


if __name__ == "__main__":
    asyncio.run(main()) 