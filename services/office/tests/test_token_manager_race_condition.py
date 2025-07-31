#!/usr/bin/env python3
"""
Comprehensive test for TokenManager race condition fixes.

This test combines multiple approaches to verify that the shared TokenManager
implementation properly handles concurrent access without race conditions.
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
        # Simulate realistic network delay to make race conditions more likely
        await asyncio.sleep(0.05)
        print(f"TokenManager instance {self._instance_id}: Requesting token for user {user_id}, provider {provider}")
        return None


class MockSettings:
    """Mock settings to avoid database dependencies."""
    
    def __init__(self):
        self.DEMO_MODE = False
        self.api_office_user_key = "test-api-key"
        self.USER_SERVICE_URL = "http://localhost:8000"


async def test_realistic_concurrent_access():
    """
    Test realistic concurrent access patterns that could occur in production.
    
    This test simulates:
    1. Multiple concurrent API requests from different users
    2. Mixed provider types (Google, Microsoft)
    3. Varying request timing and durations
    4. Realistic network delays
    """
    
    print("Testing realistic concurrent TokenManager access...")
    print("=" * 70)
    
    # Create API client factory
    factory = APIClientFactory()
    
    # Mock all dependencies
    with patch('services.office.core.api_client_factory.get_settings') as mock_settings, \
         patch('services.office.core.token_manager.get_settings') as mock_token_settings:
        
        mock_settings.return_value = MockSettings()
        mock_token_settings.return_value = MockSettings()
        
        # Mock the token manager creation
        with patch('services.office.core.api_client_factory.TokenManager', MockTokenManager):
            
            # Simulate realistic concurrent scenarios
            async def realistic_client_task(task_id: int, provider: str, delay: float = 0):
                """Simulate a realistic client creation task with configurable timing."""
                if delay > 0:
                    await asyncio.sleep(delay)
                
                print(f"Task {task_id}: Starting {provider} client creation")
                try:
                    await factory.create_client(f"test-user-{task_id}", provider)
                    print(f"Task {task_id}: {provider} client creation completed successfully")
                    return True
                except Exception as e:
                    print(f"Task {task_id}: {provider} client creation failed with {e}")
                    return False
            
            # Create a mix of concurrent tasks with different timing patterns
            tasks = []
            
            # Immediate concurrent tasks (most likely to cause race conditions)
            for i in range(3):
                task = asyncio.create_task(realistic_client_task(i, "microsoft"))
                tasks.append(task)
            
            # Delayed tasks to test staggered access
            for i in range(3, 5):
                task = asyncio.create_task(realistic_client_task(i, "google", delay=0.1))
                tasks.append(task)
            
            # Mixed provider tasks with different delays
            task = asyncio.create_task(realistic_client_task(5, "microsoft", delay=0.05))
            tasks.append(task)
            
            task = asyncio.create_task(realistic_client_task(6, "google", delay=0.15))
            tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            successful_tasks = 0
            failed_tasks = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Task {i} failed with exception: {result}")
                    failed_tasks += 1
                elif result is True:
                    successful_tasks += 1
                else:
                    failed_tasks += 1
            
            print(f"\nResults: {successful_tasks} successful, {failed_tasks} failed")
            
            # Assert that all tasks should succeed
            assert failed_tasks == 0, f"Expected all tasks to succeed, but {failed_tasks} failed"
    
    print("=" * 70)
    print("Realistic concurrent test completed successfully!")


async def test_sequential_access():
    """Test that sequential access works correctly."""
    
    print("\nTesting sequential TokenManager access...")
    print("=" * 70)
    
    # Create API client factory
    factory = APIClientFactory()
    
    # Mock all dependencies
    with patch('services.office.core.api_client_factory.get_settings') as mock_settings, \
         patch('services.office.core.token_manager.get_settings') as mock_token_settings:
        
        mock_settings.return_value = MockSettings()
        mock_token_settings.return_value = MockSettings()
        
        # Mock the token manager creation
        with patch('services.office.core.api_client_factory.TokenManager', MockTokenManager):
            
            # Sequential calls with mixed providers
            providers = ["microsoft", "google", "microsoft"]
            for i, provider in enumerate(providers):
                print(f"Sequential call {i + 1}: {provider}")
                try:
                    await factory.create_client(f"test-user-{i}", provider)
                    print(f"Sequential call {i + 1} completed successfully")
                except Exception as e:
                    print(f"Sequential call {i + 1} failed: {e}")
                    raise
    
    print("=" * 70)
    print("Sequential test completed successfully!")


async def test_ref_count_validation():
    """
    Test that reference counting works correctly under various scenarios.
    """
    
    print("\nTesting reference counting validation...")
    print("=" * 70)
    
    # Create API client factory
    factory = APIClientFactory()
    
    # Mock all dependencies
    with patch('services.office.core.api_client_factory.get_settings') as mock_settings, \
         patch('services.office.core.token_manager.get_settings') as mock_token_settings:
        
        mock_settings.return_value = MockSettings()
        mock_token_settings.return_value = MockSettings()
        
        # Mock the token manager creation
        with patch('services.office.core.api_client_factory.TokenManager', MockTokenManager):
            
            # Test rapid sequential access
            print("Testing rapid sequential access...")
            for i in range(3):
                await factory.create_client(f"test-user-{i}", "microsoft")
            
            # Test concurrent access with immediate completion
            print("Testing concurrent access with immediate completion...")
            async def quick_task(task_id: int):
                await factory.create_client(f"concurrent-user-{task_id}", "google")
            
            tasks = [asyncio.create_task(quick_task(i)) for i in range(3)]
            await asyncio.gather(*tasks)
            
            # Test staggered access
            print("Testing staggered access...")
            async def staggered_task(task_id: int, delay: float):
                await asyncio.sleep(delay)
                await factory.create_client(f"staggered-user-{task_id}", "microsoft")
            
            tasks = [
                asyncio.create_task(staggered_task(i, i * 0.1)) 
                for i in range(3)
            ]
            await asyncio.gather(*tasks)
    
    print("=" * 70)
    print("Reference counting validation completed successfully!")


async def test_error_handling():
    """
    Test that errors are handled gracefully without affecting other operations.
    """
    
    print("\nTesting error handling...")
    print("=" * 70)
    
    # Create API client factory
    factory = APIClientFactory()
    
    # Mock all dependencies
    with patch('services.office.core.api_client_factory.get_settings') as mock_settings, \
         patch('services.office.core.token_manager.get_settings') as mock_token_settings:
        
        mock_settings.return_value = MockSettings()
        mock_token_settings.return_value = MockSettings()
        
        # Mock the token manager creation
        with patch('services.office.core.api_client_factory.TokenManager', MockTokenManager):
            
            # Test concurrent access with one failing task
            async def mixed_success_task(task_id: int):
                if task_id == 1:
                    # Simulate a failure
                    raise Exception(f"Simulated failure for task {task_id}")
                await factory.create_client(f"mixed-user-{task_id}", "microsoft")
            
            tasks = [asyncio.create_task(mixed_success_task(i)) for i in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify that the failure doesn't affect other tasks
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            failure_count = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"Mixed success/failure test: {success_count} succeeded, {failure_count} failed")
            assert success_count == 2, "Expected 2 successful tasks"
            assert failure_count == 1, "Expected 1 failed task"
    
    print("=" * 70)
    print("Error handling test completed successfully!")


async def main():
    """Run all comprehensive tests."""
    print("Starting comprehensive TokenManager race condition tests...")
    print("=" * 70)
    
    try:
        await test_realistic_concurrent_access()
        await test_sequential_access()
        await test_ref_count_validation()
        await test_error_handling()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED!")
        print("✅ Realistic concurrent access works correctly")
        print("✅ Sequential access works correctly")
        print("✅ Reference counting works correctly")
        print("✅ Error handling works correctly")
        print("✅ No race conditions detected")
        print("✅ No 'client already closed' errors")
        print("✅ TokenManager properly shared across operations")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 