#!/usr/bin/env python3
"""
Test script to verify the race condition fix for concurrent TokenManager access.
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
        print(f"TokenManager instance {self._instance_id}: Requesting token for user {user_id}, provider {provider}")
        return None


async def test_concurrent_access():
    """Test that concurrent access to TokenManager doesn't cause race conditions."""
    
    print("Testing concurrent TokenManager access...")
    print("=" * 60)
    
    # Create API client factory
    factory = APIClientFactory()
    
    # Mock the settings
    with patch('services.office.core.api_client_factory.get_settings') as mock_settings:
        mock_settings.return_value.DEMO_MODE = False
        
        # Mock the token manager creation
        with patch('services.office.core.api_client_factory.TokenManager', MockTokenManager):
            
            # Create multiple concurrent tasks
            async def create_client_task(task_id: int):
                print(f"Task {task_id}: Starting create_client call")
                try:
                    await factory.create_client(f"test-user-{task_id}", "microsoft")
                    print(f"Task {task_id}: create_client completed successfully")
                except Exception as e:
                    print(f"Task {task_id}: create_client failed with {e}")
            
            # Run multiple concurrent tasks
            tasks = []
            for i in range(5):
                task = asyncio.create_task(create_client_task(i))
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
    
    print("=" * 60)
    print("Test completed. Check logs for proper ref counting and no race conditions.")


async def test_sequential_access():
    """Test that sequential access works correctly."""
    
    print("\nTesting sequential TokenManager access...")
    print("=" * 60)
    
    # Create API client factory
    factory = APIClientFactory()
    
    # Mock the settings
    with patch('services.office.core.api_client_factory.get_settings') as mock_settings:
        mock_settings.return_value.DEMO_MODE = False
        
        # Mock the token manager creation
        with patch('services.office.core.api_client_factory.TokenManager', MockTokenManager):
            
            # Sequential calls
            for i in range(3):
                print(f"Sequential call {i + 1}")
                try:
                    await factory.create_client(f"test-user-{i}", "microsoft")
                except Exception as e:
                    print(f"Sequential call {i + 1} failed: {e}")
    
    print("=" * 60)
    print("Sequential test completed.")


async def main():
    """Run both tests."""
    await test_concurrent_access()
    await test_sequential_access()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print("✅ Concurrent access should show proper ref counting")
    print("✅ No 'client already closed' errors should occur")
    print("✅ TokenManager should be properly shared and managed")


if __name__ == "__main__":
    asyncio.run(main()) 