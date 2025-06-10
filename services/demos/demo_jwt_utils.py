#!/usr/bin/env python3
"""
JWT utilities for user management service demos.

This module provides utilities for creating and working with JWT tokens
that are compatible with the user management service's authentication system.

The service now supports both Clerk's official SDK verification and manual 
verification with configurable signature verification:

- With CLERK_SECRET_KEY: Uses Clerk's authenticate_request() method (recommended)
- With CLERK_JWT_KEY: Uses networkless verification with Clerk's public key
- Fallback: Manual verification with configurable signature verification

Environment Variables:
- CLERK_SECRET_KEY: Clerk secret key for full SDK verification
- CLERK_JWT_KEY: Clerk JWKS public key for networkless verification  
- JWT_VERIFY_SIGNATURE: Enable signature verification (default: False for demos)
"""

import time
from typing import Dict, Any

try:
    import jwt
except ImportError:
    print("❌ PyJWT not installed. Install with: pip install PyJWT")
    exit(1)


def create_demo_jwt_token(user_id: str, email: str = None) -> str:
    """
    Create a valid JWT token for demo purposes.
    
    Args:
        user_id: User ID to include in token
        email: User email to include in token
        
    Returns:
        Valid JWT token string
    """
    now = int(time.time())
    
    # Create JWT payload with required claims
    payload = {
        "sub": user_id,  # Subject (user ID)
        "iss": "https://clerk.demo.com",  # Issuer (demo Clerk domain)
        "aud": "demo-audience",  # Audience
        "exp": now + 3600,  # Expires in 1 hour
        "iat": now,  # Issued at
        "nbf": now,  # Not before
        "jti": f"demo-token-{user_id}-{now}",  # JWT ID
    }
    
    # Add email if provided
    if email:
        payload["email"] = email
        payload["email_verified"] = True
    
    # Add demo permissions
    payload["permissions"] = ["read", "write", "admin"]
    
    # Create JWT token (unsigned for demo - signature verification is disabled in auth code)
    # Use HS256 algorithm for simplicity in demos
    token = jwt.encode(
        payload,
        "demo-secret-key",  # Demo secret (signature verification disabled anyway)
        algorithm="HS256",   # Simple algorithm for demo
    )
    
    return token


def get_demo_tokens() -> Dict[str, str]:
    """
    Get pre-generated demo tokens for common demo users.
    
    Returns:
        Dictionary mapping user IDs to JWT tokens
    """
    demo_users = {
        "demo_user_12345": "demo.user@example.com",
        "simple_demo_user_123": "simple.demo@example.com",
        "test_user_456": "test.user@example.com",
    }
    
    tokens = {}
    for user_id, email in demo_users.items():
        tokens[user_id] = create_demo_jwt_token(user_id, email)
    
    return tokens


def create_bearer_token(user_id: str, email: str = None) -> str:
    """
    Create a Bearer token string for Authorization header.
    
    Args:
        user_id: User ID to include in token
        email: User email to include in token
        
    Returns:
        Bearer token string ready for Authorization header
    """
    jwt_token = create_demo_jwt_token(user_id, email)
    return f"Bearer {jwt_token}"


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token and return claims.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing token claims
        
    Raises:
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        # Decode without signature verification (matches the service behavior)
        # Try RS256 first (service expectation), then HS256 (fallback)
        for algorithm in ["RS256", "HS256"]:
            try:
                decoded = jwt.decode(
                    token,
                    options={"verify_signature": False},
                    algorithms=[algorithm]
                )
                return decoded
            except jwt.InvalidTokenError:
                continue
        
        # If both fail, raise the error
        raise jwt.InvalidTokenError("Token could not be decoded with supported algorithms")
        
    except jwt.InvalidTokenError as e:
        print(f"Failed to decode token: {e}")
        raise


if __name__ == "__main__":
    # Demo usage
    print("🎫 Demo JWT Token Generator")
    print("=" * 40)
    
    # Generate tokens for demo users
    tokens = get_demo_tokens()
    
    for user_id, token in tokens.items():
        print(f"\n👤 User: {user_id}")
        print(f"🎫 JWT: {token[:50]}...")
        print(f"🔐 Bearer: Bearer {token[:30]}...")
    
    # Test token creation
    print(f"\n🧪 Test token for demo_user_12345:")
    test_token = create_demo_jwt_token("demo_user_12345", "demo.user@example.com")
    print(f"🎫 {test_token}")
    
    # Decode and verify
    try:
        decoded = jwt.decode(test_token, "demo-secret-key", algorithms=["HS256"])
        print(f"\n✅ Token decoded successfully:")
        print(f"   👤 User ID: {decoded['sub']}")
        print(f"   📧 Email: {decoded.get('email', 'N/A')}")
        print(f"   ⏰ Expires: {decoded['exp']}")
    except Exception as e:
        print(f"\n❌ Token decode failed: {e}") 