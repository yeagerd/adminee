#!/usr/bin/env python3
"""
NextAuth Test Server for Briefly Demo

This server simulates NextAuth functionality to test Google/Microsoft OAuth flows
without requiring a full Next.js setup. It provides endpoints that mimic NextAuth's
behavior for testing with the chat.py demo.

Features:
- Google OAuth simulation
- Microsoft OAuth simulation  
- JWT token generation (simulating NextAuth tokens)
- User creation/management
- Token validation

Usage:
    python services/demos/nextauth_test_server.py

Environment Variables:
    GOOGLE_CLIENT_ID        Google OAuth client ID
    GOOGLE_CLIENT_SECRET    Google OAuth client secret
    MICROSOFT_CLIENT_ID     Microsoft OAuth client ID
    MICROSOFT_CLIENT_SECRET Microsoft OAuth client secret
    NEXTAUTH_SECRET         Secret for JWT signing (default: demo-secret)
"""

import asyncio
import json
import logging
import os
import secrets
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import jwt
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET", "demo-nextauth-secret")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")

# In-memory storage for demo purposes
users_db: Dict[str, Dict] = {}
sessions_db: Dict[str, Dict] = {}
oauth_states: Dict[str, Dict] = {}

app = FastAPI(title="NextAuth Test Server", version="1.0.0")


class OAuthStartRequest(BaseModel):
    """Request to start OAuth flow."""
    provider: str
    redirect_uri: str = "http://localhost:3000/api/auth/callback"
    scopes: Optional[List[str]] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback request."""
    code: str
    state: str


class NextAuthToken(BaseModel):
    """NextAuth JWT token structure."""
    sub: str  # User ID
    email: str
    name: str
    provider: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: Optional[int] = None
    iat: int
    exp: int


def generate_state() -> str:
    """Generate a secure random state for OAuth."""
    return secrets.token_urlsafe(32)


def create_nextauth_jwt(user_data: Dict, provider: str, tokens: Dict = None) -> str:
    """Create a NextAuth-style JWT token."""
    now = int(time.time())
    expires = now + 3600  # 1 hour
    
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "name": user_data.get("name", user_data["email"]),
        "provider": provider,
        "iat": now,
        "exp": expires,
    }
    
    # Add OAuth tokens if available
    if tokens:
        payload.update({
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": tokens.get("expires_at"),
        })
    
    return jwt.encode(payload, NEXTAUTH_SECRET, algorithm="HS256")


def verify_nextauth_jwt(token: str) -> Dict:
    """Verify and decode NextAuth JWT token."""
    try:
        payload = jwt.decode(token, NEXTAUTH_SECRET, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}"
        )


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "NextAuth Test Server",
        "version": "1.0.0",
        "endpoints": {
            "oauth_start": "/auth/oauth/start",
            "oauth_callback": "/auth/oauth/callback/{provider}",
            "session": "/auth/session",
            "users": "/users",
        },
        "providers": {
            "google": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
            "microsoft": bool(MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET),
        }
    }


@app.post("/auth/oauth/start")
async def start_oauth_flow(request: OAuthStartRequest):
    """Start OAuth flow for Google or Microsoft."""
    provider = request.provider.lower()
    
    if provider not in ["google", "microsoft"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported providers: google, microsoft"
        )
    
    # Generate state
    state = generate_state()
    oauth_states[state] = {
        "provider": provider,
        "redirect_uri": request.redirect_uri,
        "scopes": request.scopes or [],
        "created_at": time.time(),
    }
    
    # Build authorization URL
    if provider == "google":
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth not configured"
            )
        
        scopes = request.scopes or [
            "openid",
            "email", 
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar"
        ]
        
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={urllib.parse.quote(request.redirect_uri)}&"
            "response_type=code&"
            f"scope={urllib.parse.quote(' '.join(scopes))}&"
            f"state={state}&"
            "access_type=offline&"
            "prompt=consent"
        )
        
    elif provider == "microsoft":
        if not MICROSOFT_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Microsoft OAuth not configured"
            )
        
        scopes = request.scopes or [
            "openid",
            "email",
            "profile", 
            "offline_access",
            "https://graph.microsoft.com/User.Read",
            "https://graph.microsoft.com/Calendars.ReadWrite",
            "https://graph.microsoft.com/Mail.Read"
        ]
        
        auth_url = (
            "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"client_id={MICROSOFT_CLIENT_ID}&"
            f"redirect_uri={urllib.parse.quote(request.redirect_uri)}&"
            "response_type=code&"
            f"scope={urllib.parse.quote(' '.join(scopes))}&"
            f"state={state}"
        )
    
    return {
        "authorization_url": auth_url,
        "state": state,
        "provider": provider,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10),
    }


@app.get("/auth/oauth/callback/{provider}")
async def oauth_callback(
    provider: str,
    code: str = Query(...),
    state: str = Query(...),
):
    """Handle OAuth callback from Google or Microsoft."""
    provider = provider.lower()
    
    # Verify state
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state"
        )
    
    state_data = oauth_states.pop(state)
    if state_data["provider"] != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider mismatch"
        )
    
    try:
        # Exchange code for tokens
        tokens = await exchange_code_for_tokens(provider, code, state_data)
        
        # Get user info
        user_info = await get_user_info(provider, tokens["access_token"])
        
        # Create or update user
        user_id = f"{provider}_{user_info['id']}"
        user_data = {
            "id": user_id,
            "email": user_info["email"],
            "name": user_info.get("name", user_info["email"]),
            "provider": provider,
            "provider_id": user_info["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
        }
        
        users_db[user_id] = user_data
        
        # Create NextAuth JWT
        jwt_token = create_nextauth_jwt(user_data, provider, tokens)
        
        # Store session
        session_id = secrets.token_urlsafe(32)
        sessions_db[session_id] = {
            "user_id": user_id,
            "jwt_token": jwt_token,
            "created_at": time.time(),
            "expires_at": time.time() + 3600,
        }
        
        logger.info(f"OAuth callback successful for {provider} user {user_info['email']}")
        
        # Return success page with token
        return HTMLResponse(f"""
        <html>
        <head><title>OAuth Success</title></head>
        <body>
            <h1>✅ Authentication Successful!</h1>
            <p><strong>Provider:</strong> {provider.title()}</p>
            <p><strong>Email:</strong> {user_info['email']}</p>
            <p><strong>Name:</strong> {user_info.get('name', 'N/A')}</p>
            
            <h2>NextAuth JWT Token:</h2>
            <textarea style="width: 100%; height: 150px; font-family: monospace; font-size: 12px;">{jwt_token}</textarea>
            
            <h2>Session Info:</h2>
            <pre>{json.dumps({
                'user_id': user_id,
                'session_id': session_id,
                'provider': provider,
                'email': user_info['email']
            }, indent=2)}</pre>
            
            <p><em>You can now use this JWT token to authenticate with Briefly services.</em></p>
            <p><a href="/">← Back to NextAuth Test Server</a></p>
        </body>
        </html>
        """)
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth callback failed: {str(e)}"
        )


async def exchange_code_for_tokens(provider: str, code: str, state_data: Dict) -> Dict:
    """Exchange authorization code for access tokens."""
    async with httpx.AsyncClient() as client:
        if provider == "google":
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": state_data["redirect_uri"],
            }
        elif provider == "microsoft":
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            data = {
                "client_id": MICROSOFT_CLIENT_ID,
                "client_secret": MICROSOFT_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": state_data["redirect_uri"],
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        response = await client.post(
            token_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
        
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.status_code} {response.text}")
        
        return response.json()


async def get_user_info(provider: str, access_token: str) -> Dict:
    """Get user information from OAuth provider."""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {access_token}"}
        
        if provider == "google":
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers,
                timeout=30.0,
            )
        elif provider == "microsoft":
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers=headers,
                timeout=30.0,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        if response.status_code != 200:
            raise Exception(f"User info request failed: {response.status_code} {response.text}")
        
        user_data = response.json()
        
        # Normalize user data structure
        if provider == "google":
            return {
                "id": user_data["id"],
                "email": user_data["email"],
                "name": user_data.get("name"),
                "picture": user_data.get("picture"),
            }
        elif provider == "microsoft":
            return {
                "id": user_data["id"],
                "email": user_data.get("mail") or user_data.get("userPrincipalName"),
                "name": user_data.get("displayName"),
                "picture": None,  # Would need separate request
            }


@app.get("/auth/session")
async def get_session(request: Request):
    """Get current session information."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header[7:]  # Remove "Bearer "
    
    try:
        payload = verify_nextauth_jwt(token)
        user_id = payload["sub"]
        
        if user_id not in users_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = users_db[user_id]
        
        return {
            "user": {
                "id": user_data["id"],
                "email": user_data["email"],
                "name": user_data["name"],
                "provider": user_data["provider"],
            },
            "expires": datetime.fromtimestamp(payload["exp"], timezone.utc).isoformat(),
            "access_token": payload.get("access_token"),
            "refresh_token": payload.get("refresh_token"),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid session: {e}"
        )


@app.get("/users")
async def list_users():
    """List all users (demo purposes)."""
    return {
        "users": list(users_db.values()),
        "total": len(users_db),
    }


@app.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get specific user information."""
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return users_db[user_id]


@app.post("/auth/verify")
async def verify_token(request: Request):
    """Verify NextAuth JWT token (for backend services)."""
    try:
        body = await request.json()
        token = body.get("token")
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token required"
            )
        
        payload = verify_nextauth_jwt(token)
        user_id = payload["sub"]
        
        if user_id not in users_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "valid": True,
            "user_id": user_id,
            "email": payload["email"],
            "provider": payload["provider"],
            "expires_at": payload["exp"],
        }
        
    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
        }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting NextAuth Test Server...")
    print("=" * 50)
    print(f"📍 Server URL: http://localhost:8090")
    print(f"🔑 NextAuth Secret: {NEXTAUTH_SECRET}")
    print(f"🟢 Google OAuth: {'✅ Configured' if GOOGLE_CLIENT_ID else '❌ Not configured'}")
    print(f"🔵 Microsoft OAuth: {'✅ Configured' if MICROSOFT_CLIENT_ID else '❌ Not configured'}")
    print()
    print("📋 Available endpoints:")
    print("  • GET  /                     - Service info")
    print("  • POST /auth/oauth/start     - Start OAuth flow")
    print("  • GET  /auth/oauth/callback  - OAuth callback")
    print("  • GET  /auth/session         - Get session info")
    print("  • POST /auth/verify          - Verify JWT token")
    print("  • GET  /users                - List users")
    print()
    print("💡 Test with chat.py demo:")
    print("  python services/demos/chat.py --nextauth")
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8090,
        log_level="info",
        access_log=True,
    ) 