#!/usr/bin/env python3
"""
Test NextAuth Integration with Briefly Services

This script tests the end-to-end integration of NextAuth users with the Briefly system.
"""

import asyncio
import time

import httpx
import jwt


# NextAuth user token
def create_nextauth_token() -> str:
    """Create a NextAuth JWT token for testing."""
    now = int(time.time())
    payload = {
        "user_id": "google_108234567890123456789",
        "sub": "google_108234567890123456789",
        "email": "nextauth.test@example.com",
        "name": "NextAuth Test",
        "provider": "google",
        "iss": "https://nextauth.demo.briefly.ai",
        "exp": now + 3600,
        "iat": now,
    }
    return jwt.encode(payload, "demo_secret", algorithm="HS256")


async def test_user_service() -> bool:
    """Test user service endpoints with NextAuth user."""
    token = create_nextauth_token()
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        print("🧪 Testing User Service with NextAuth user...")

        # Test user profile
        response = await client.get(
            "http://localhost:8001/users/google_108234567890123456789", headers=headers
        )
        if response.status_code == 200:
            user_data = response.json()
            print(
                f"✅ User Profile: {user_data['email']} (Provider: {user_data['auth_provider']})"
            )
        else:
            print(f"❌ User Profile failed: {response.status_code}")
            return False

        # Test user preferences
        response = await client.get(
            "http://localhost:8001/users/google_108234567890123456789/preferences/",
            headers=headers,
        )
        if response.status_code == 200:
            prefs_data = response.json()
            print(
                f"✅ User Preferences: {prefs_data['user_id']} (Timezone: {prefs_data['ui']['timezone']})"
            )
        else:
            print(f"❌ User Preferences failed: {response.status_code}")
            return False

        return True


async def test_internal_service() -> bool:
    """Test internal service endpoints with NextAuth user."""
    headers = {"X-API-Key": "test-CHAT_USER_KEY"}

    async with httpx.AsyncClient() as client:
        print("🧪 Testing Internal Service with NextAuth user...")

        # Test internal preferences
        response = await client.get(
            "http://localhost:8001/v1/internal/users/google_108234567890123456789/preferences",
            headers=headers,
        )
        if response.status_code == 200:
            prefs_data = response.json()
            print(f"✅ Internal Preferences: {prefs_data['user_id']}")
        else:
            print(f"❌ Internal Preferences failed: {response.status_code}")
            return False

        return True


async def test_chat_service() -> bool:
    """Test chat service with NextAuth user."""
    token = create_nextauth_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        print("🧪 Testing Chat Service with NextAuth user...")

        # Test chat endpoint
        chat_data = {
            "message": "Hello from NextAuth user!",
            "user_id": "google_108234567890123456789",
        }

        response = await client.post(
            "http://localhost:8002/chat", headers=headers, json=chat_data
        )
        if response.status_code == 200:
            chat_response = response.json()
            print("✅ Chat Service: Message sent successfully")
            print(
                f"   Response: {chat_response.get('response', 'No response')[:100]}..."
            )
        else:
            print(f"❌ Chat Service failed: {response.status_code}")
            if response.status_code != 200:
                print(f"   Error: {response.text[:200]}")
            return False

        return True


async def main() -> bool:
    """Run all integration tests."""
    print("🚀 NextAuth Integration Test Suite")
    print("=" * 50)

    # Test services in sequence
    tests = [
        ("User Service", test_user_service),
        ("Internal Service", test_internal_service),
        ("Chat Service", test_chat_service),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
            print()
        except Exception as e:
            print(f"❌ {test_name} error: {e}")
            results[test_name] = False
            print()

    # Summary
    print("📊 Test Results Summary:")
    print("=" * 30)
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("🎉 All tests passed! NextAuth integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
