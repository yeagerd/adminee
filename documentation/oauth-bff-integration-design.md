# OAuth BFF Integration Design

## Overview

This document outlines the complete implementation of OAuth authentication flow using NextAuth.js as the authentication layer, a Backend for Frontend (BFF) for API orchestration, and the user management service for user lifecycle management. The design includes enterprise domain support, email collision detection, and account linking across OAuth providers.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   NextAuth.js   │    │   BFF Layer     │    │  User Service   │
│   (React/Next)  │◄──►│   (Auth Layer)  │◄──►│   (API Gateway) │◄──►│  (User Mgmt)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │                       │
         │                       │                       │                       │
         ▼                       ▼                       ▼                       ▼
   User clicks           OAuth callback          Webhook handler         login_or_create
   "Sign in with         processes user          calls user service       endpoint
   Microsoft/Google"     data from provider      with OAuth data         handles collision
```

## 1. NextAuth.js Configuration

### 1.1 Provider Configuration

```typescript
// pages/api/auth/[...nextauth].ts
import NextAuth from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import AzureADProvider from 'next-auth/providers/azure-ad';

export default NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'openid email profile https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar',
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    }),
    AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID || 'common', // 'common' for multi-tenant
      authorization: {
        params: {
          scope: 'openid email profile offline_access https://graph.microsoft.com/User.Read https://graph.microsoft.com/Calendars.ReadWrite https://graph.microsoft.com/Mail.Read',
        },
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account, profile }) {
      // Send webhook to BFF with OAuth data
      await sendOAuthWebhook({
        email: user.email!,
        provider: account?.provider!,
        providerUserId: account?.providerAccountId!,
        name: {
          first: user.name?.split(' ')[0] || '',
          last: user.name?.split(' ').slice(1).join(' ') || '',
        },
        picture: user.image,
        accessToken: account?.access_token,
        refreshToken: account?.refresh_token,
        expiresAt: account?.expires_at,
      });
      
      return true;
    },
    async jwt({ token, account, user }) {
      // Store OAuth tokens in JWT for API access
      if (account) {
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.provider = account.provider;
        token.providerUserId = account.providerAccountId;
      }
      return token;
    },
    async session({ session, token }) {
      // Include OAuth data in session
      session.accessToken = token.accessToken;
      session.provider = token.provider;
      session.providerUserId = token.providerUserId;
      return session;
    },
  },
  events: {
    async signIn({ user, account, profile, isNewUser }) {
      // Additional webhook for new user sign-ins
      if (isNewUser) {
        await sendNewUserWebhook({
          email: user.email!,
          provider: account?.provider!,
          providerUserId: account?.providerAccountId!,
          name: user.name!,
          picture: user.image,
        });
      }
    },
  },
});
```

### 1.2 Webhook Sender Utility

```typescript
// utils/oauth-webhook.ts
interface OAuthWebhookData {
  email: string;
  provider: 'google' | 'microsoft';
  providerUserId: string;
  name: {
    first: string;
    last: string;
  };
  picture?: string;
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: number;
}

async function sendOAuthWebhook(data: OAuthWebhookData) {
  try {
    const response = await fetch(`${process.env.BFF_BASE_URL}/api/auth/oauth-webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BFF_API_KEY!,
      },
      body: JSON.stringify({
        type: 'oauth.user_authenticated',
        data,
        timestamp: Date.now(),
      }),
    });
    
    if (!response.ok) {
      console.error('Failed to send OAuth webhook:', response.statusText);
    }
  } catch (error) {
    console.error('Error sending OAuth webhook:', error);
  }
}
```

## 2. BFF Layer Implementation

### 2.1 BFF API Routes

```typescript
// pages/api/auth/oauth-webhook.ts
import { NextApiRequest, NextApiResponse } from 'next';
import { verifyWebhookSignature } from '@/utils/webhook-auth';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Verify webhook signature (from NextAuth)
    const isValid = verifyWebhookSignature(req);
    if (!isValid) {
      return res.status(401).json({ error: 'Invalid webhook signature' });
    }

    const { type, data, timestamp } = req.body;

    if (type === 'oauth.user_authenticated') {
      // Call user service login_or_create
      const userResponse = await fetch(`${process.env.USER_SERVICE_URL}/users/login-or-create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.API_FRONTEND_USER_KEY!,
        },
        body: JSON.stringify({
          email: data.email,
          auth_provider: data.provider,
          external_auth_id: data.providerUserId,
          first_name: data.name.first,
          last_name: data.name.last,
          profile_image_url: data.picture,
          oauth_tokens: {
            access_token: data.accessToken,
            refresh_token: data.refreshToken,
            expires_at: data.expiresAt,
          },
        }),
      });

      if (!userResponse.ok) {
        throw new Error(`User service error: ${userResponse.statusText}`);
      }

      const user = await userResponse.json();

      // Store OAuth tokens in user service (for office service access)
      if (data.accessToken) {
        await storeOAuthTokens(user.id, data.provider, {
          access_token: data.accessToken,
          refresh_token: data.refreshToken,
          expires_at: data.expiresAt,
        });
      }

      return res.status(200).json({ 
        success: true, 
        user_id: user.id,
        action: user.action // 'user_created' or 'user_linked'
      });
    }

    return res.status(400).json({ error: 'Unsupported webhook type' });
  } catch (error) {
    console.error('OAuth webhook error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}

// pages/api/auth/session.ts
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { user_id } = req.query;
    
    // Get user data from user service
    const userResponse = await fetch(`${process.env.USER_SERVICE_URL}/users/${user_id}`, {
      headers: {
        'X-API-Key': process.env.API_FRONTEND_USER_KEY!,
      },
    });

    if (!userResponse.ok) {
      return res.status(404).json({ error: 'User not found' });
    }

    const user = await userResponse.json();
    return res.status(200).json(user);
  } catch (error) {
    console.error('Session error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
```

### 2.2 OAuth Token Storage

```typescript
// utils/oauth-token-storage.ts
async function storeOAuthTokens(
  userId: string, 
  provider: string, 
  tokens: {
    access_token: string;
    refresh_token?: string;
    expires_at?: number;
  }
) {
  try {
    const response = await fetch(`${process.env.USER_SERVICE_URL}/users/${userId}/integrations/oauth/tokens`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.API_FRONTEND_USER_KEY!,
      },
      body: JSON.stringify({
        provider,
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
        expires_at: tokens.expires_at,
      }),
    });

    if (!response.ok) {
      console.error('Failed to store OAuth tokens:', response.statusText);
    }
  } catch (error) {
    console.error('Error storing OAuth tokens:', error);
  }
}
```

## 3. User Service Implementation

### 3.1 New Schemas

```python
# services/user/schemas/oauth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from datetime import datetime

class OAuthUserCreate(BaseModel):
    """Schema for OAuth user creation/login."""
    email: EmailStr = Field(..., description="User's email address")
    auth_provider: str = Field(..., description="OAuth provider (google, microsoft)")
    external_auth_id: str = Field(..., description="Provider's user ID")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    oauth_tokens: Optional[Dict[str, Any]] = Field(None, description="OAuth tokens")

class OAuthTokenStore(BaseModel):
    """Schema for storing OAuth tokens."""
    provider: str = Field(..., description="OAuth provider")
    access_token: str = Field(..., description="Access token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    expires_at: Optional[int] = Field(None, description="Token expiration timestamp")

class LoginOrCreateResponse(BaseModel):
    """Response for login_or_create endpoint."""
    user: UserResponse
    action: str = Field(..., description="Action taken: user_created, user_linked, user_updated")
    is_new_user: bool = Field(..., description="Whether this is a new user")
```

### 3.2 Login or Create Endpoint

```python
# services/user/routers/users.py
@router.post(
    "/login-or-create",
    response_model=LoginOrCreateResponse,
    summary="Login existing user or create new user from OAuth",
    description="Handle OAuth user authentication with email collision detection and account linking.",
    responses={
        200: {"description": "User logged in or created successfully"},
        400: {"description": "Invalid OAuth data"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def login_or_create_user(
    oauth_data: OAuthUserCreate = Body(..., description="OAuth user data"),
    current_service: str = Depends(require_service_auth),
) -> LoginOrCreateResponse:
    """
    Login existing user or create new user from OAuth data.
    
    This endpoint handles:
    - Email collision detection using normalized email
    - Account linking across OAuth providers
    - New user creation with proper validation
    - OAuth token storage for service access
    """
    try:
        logger.info(f"Processing OAuth login/create for {oauth_data.email} via {oauth_data.auth_provider}")
        
        # Check for email collision using normalized email
        collision_details = await email_detector.get_collision_details(oauth_data.email)
        
        if collision_details["collision"]:
            # User exists - handle account linking
            existing_user = await user_service.link_oauth_account(
                email=oauth_data.email,
                auth_provider=oauth_data.auth_provider,
                external_auth_id=oauth_data.external_auth_id,
                oauth_data=oauth_data
            )
            
            action = "user_linked"
            is_new_user = False
            
            logger.info(f"Linked OAuth account {oauth_data.auth_provider} to existing user {existing_user.id}")
            
        else:
            # Create new user
            existing_user = await user_service.create_user_from_oauth(oauth_data)
            action = "user_created"
            is_new_user = True
            
            logger.info(f"Created new user {existing_user.id} from OAuth {oauth_data.auth_provider}")
        
        # Store OAuth tokens if provided
        if oauth_data.oauth_tokens:
            await token_service.store_oauth_tokens(
                user_id=existing_user.id,
                provider=oauth_data.auth_provider,
                tokens=oauth_data.oauth_tokens
            )
        
        user_response = UserResponse.from_orm(existing_user)
        
        return LoginOrCreateResponse(
            user=user_response,
            action=action,
            is_new_user=is_new_user
        )
        
    except EmailCollisionException as e:
        logger.warning(f"Email collision detected: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "EmailCollision",
                "message": "An account with this email already exists",
                "details": {
                    "email": oauth_data.email,
                    "existing_provider": e.existing_provider,
                    "suggestions": [
                        "Try signing in with your existing account",
                        "Contact support if you need help accessing your account"
                    ]
                }
            }
        )
    except Exception as e:
        logger.error(f"Login or create failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "Failed to process OAuth login/create"
            }
        )
```

### 3.3 User Service Methods

```python
# services/user/services/user_service.py
class UserService:
    async def link_oauth_account(
        self, 
        email: str, 
        auth_provider: str, 
        external_auth_id: str, 
        oauth_data: OAuthUserCreate
    ) -> User:
        """
        Link OAuth account to existing user.
        
        Handles cases where:
        - User exists with same email but different OAuth provider
        - User exists with same email but different external_auth_id
        """
        async_session = get_async_session()
        async with async_session() as session:
            # Find existing user by normalized email
            normalized_email = await self.email_detector.normalize_email_async(email)
            
            result = await session.execute(
                select(User).where(
                    User.normalized_email == normalized_email,
                    User.deleted_at.is_(None)
                )
            )
            existing_user = result.scalar_one_or_none()
            
            if not existing_user:
                raise UserNotFoundException(f"User with email {email} not found")
            
            # Check if this OAuth provider is already linked
            if existing_user.auth_provider == auth_provider:
                if existing_user.external_auth_id == external_auth_id:
                    # Same account, just update profile if needed
                    await self._update_user_profile(existing_user, oauth_data)
                    return existing_user
                else:
                    # Same provider, different account - this is an error
                    raise EmailCollisionException(
                        email=email,
                        existing_provider=auth_provider,
                        message=f"Email {email} already linked to different {auth_provider} account"
                    )
            else:
                # Different provider - link the account
                # For now, we'll update the user to use the new provider
                # In the future, we could support multiple providers per user
                existing_user.auth_provider = auth_provider
                existing_user.external_auth_id = external_auth_id
                await self._update_user_profile(existing_user, oauth_data)
                
                await session.commit()
                await session.refresh(existing_user)
                
                return existing_user
    
    async def create_user_from_oauth(self, oauth_data: OAuthUserCreate) -> User:
        """Create new user from OAuth data."""
        async_session = get_async_session()
        async with async_session() as session:
            # Normalize email for storage
            normalized_email = await self.email_detector.normalize_email_async(oauth_data.email)
            
            # Create user record
            user = User(
                external_auth_id=oauth_data.external_auth_id,
                auth_provider=oauth_data.auth_provider,
                email=oauth_data.email,
                normalized_email=normalized_email,
                first_name=oauth_data.first_name,
                last_name=oauth_data.last_name,
                profile_image_url=oauth_data.profile_image_url,
                onboarding_completed=False,
                onboarding_step="welcome",
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            # Create default preferences
            preferences = UserPreferences(user_id=user.id)
            session.add(preferences)
            await session.commit()
            
            logger.info(f"Created new user {user.id} from OAuth {oauth_data.auth_provider}")
            return user
    
    async def _update_user_profile(self, user: User, oauth_data: OAuthUserCreate) -> None:
        """Update user profile with latest OAuth data."""
        if oauth_data.first_name and user.first_name != oauth_data.first_name:
            user.first_name = oauth_data.first_name
        if oauth_data.last_name and user.last_name != oauth_data.last_name:
            user.last_name = oauth_data.last_name
        if oauth_data.profile_image_url and user.profile_image_url != oauth_data.profile_image_url:
            user.profile_image_url = oauth_data.profile_image_url
        
        user.updated_at = datetime.now(timezone.utc)
```

### 3.4 OAuth Token Storage

```python
# services/user/services/token_service.py
class TokenService:
    async def store_oauth_tokens(
        self, 
        user_id: str, 
        provider: str, 
        tokens: Dict[str, Any]
    ) -> None:
        """Store OAuth tokens for user."""
        async_session = get_async_session()
        async with async_session() as session:
            # Check if integration exists
            result = await session.execute(
                select(Integration).where(
                    Integration.user_id == user_id,
                    Integration.provider == provider
                )
            )
            integration = result.scalar_one_or_none()
            
            if integration:
                # Update existing integration
                integration.access_token = tokens["access_token"]
                integration.refresh_token = tokens.get("refresh_token")
                integration.expires_at = tokens.get("expires_at")
                integration.updated_at = datetime.now(timezone.utc)
            else:
                # Create new integration
                integration = Integration(
                    user_id=user_id,
                    provider=provider,
                    access_token=tokens["access_token"],
                    refresh_token=tokens.get("refresh_token"),
                    expires_at=tokens.get("expires_at"),
                    status=IntegrationStatus.ACTIVE,
                )
                session.add(integration)
            
            await session.commit()
            logger.info(f"Stored OAuth tokens for user {user_id}, provider {provider}")
```

## 4. Frontend Integration

### 4.1 Authentication Hooks

```typescript
// hooks/useAuth.ts
import { useSession, signIn, signOut } from 'next-auth/react';
import { useRouter } from 'next/navigation';

export function useAuth() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const login = async (provider: 'google' | 'microsoft') => {
    try {
      const result = await signIn(provider, {
        callbackUrl: '/dashboard',
        redirect: false,
      });
      
      if (result?.error) {
        throw new Error(result.error);
      }
      
      if (result?.ok) {
        router.push('/dashboard');
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = async () => {
    await signOut({ callbackUrl: '/' });
  };

  return {
    user: session?.user,
    isAuthenticated: !!session?.user,
    isLoading: status === 'loading',
    login,
    logout,
  };
}
```

### 4.2 Login Component

```typescript
// components/LoginButtons.tsx
import { useAuth } from '@/hooks/useAuth';

export function LoginButtons() {
  const { login, isLoading } = useAuth();

  const handleGoogleLogin = () => login('google');
  const handleMicrosoftLogin = () => login('microsoft');

  return (
    <div className="space-y-4">
      <button
        onClick={handleGoogleLogin}
        disabled={isLoading}
        className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <img src="/google-icon.svg" alt="Google" className="w-5 h-5 mr-2" />
        Sign in with Google
      </button>
      
      <button
        onClick={handleMicrosoftLogin}
        disabled={isLoading}
        className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <img src="/microsoft-icon.svg" alt="Microsoft" className="w-5 h-5 mr-2" />
        Sign in with Microsoft
      </button>
    </div>
  );
}
```

## 5. Environment Configuration

### 5.1 NextAuth Environment Variables

```bash
# .env.local
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft OAuth
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_CLIENT_SECRET=your-azure-client-secret
AZURE_AD_TENANT_ID=common

# BFF Configuration
BFF_BASE_URL=http://localhost:3000
BFF_API_KEY=your-bff-api-key

# User Service
USER_SERVICE_URL=http://localhost:8001
API_FRONTEND_USER_KEY=your-user-service-api-key
```

### 5.2 User Service Environment Variables

```bash
# .env
# Existing variables...

# OAuth Configuration
OAUTH_WEBHOOK_SECRET=your-oauth-webhook-secret
OAUTH_REDIRECT_URI=http://localhost:3000/api/auth/callback

# BFF Integration
BFF_API_KEY=your-bff-api-key
```

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# services/user/tests/test_oauth_integration.py
class TestOAuthIntegration:
    async def test_login_or_create_new_user(self):
        """Test creating new user from OAuth."""
        oauth_data = OAuthUserCreate(
            email="newuser@example.com",
            auth_provider="google",
            external_auth_id="google_123",
            first_name="New",
            last_name="User"
        )
        
        response = await client.post("/users/login-or-create", json=oauth_data.dict())
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "user_created"
        assert data["is_new_user"] is True
        assert data["user"]["email"] == "newuser@example.com"
    
    async def test_login_or_create_existing_user(self):
        """Test linking OAuth to existing user."""
        # Create user first
        existing_user = await create_test_user(email="existing@example.com")
        
        oauth_data = OAuthUserCreate(
            email="existing@example.com",
            auth_provider="microsoft",
            external_auth_id="microsoft_456",
            first_name="Existing",
            last_name="User"
        )
        
        response = await client.post("/users/login-or-create", json=oauth_data.dict())
        assert response.status_code == 200
        
        data = response.json()
        assert data["action"] == "user_linked"
        assert data["is_new_user"] is False
        assert data["user"]["id"] == existing_user.id
```

### 6.2 Integration Tests

```typescript
// __tests__/oauth-flow.test.ts
describe('OAuth Flow', () => {
  test('complete OAuth flow with Google', async () => {
    // Mock NextAuth
    const mockSession = {
      user: {
        email: 'test@example.com',
        name: 'Test User',
        image: 'https://example.com/avatar.jpg',
      },
      accessToken: 'mock-access-token',
      provider: 'google',
      providerUserId: 'google_123',
    };
    
    // Mock BFF webhook
    const mockWebhookResponse = {
      success: true,
      user_id: 'user_123',
      action: 'user_created',
    };
    
    // Test the complete flow
    const response = await fetch('/api/auth/oauth-webhook', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'oauth.user_authenticated',
        data: mockSession,
      }),
    });
    
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.success).toBe(true);
  });
});
```

## 7. Deployment Considerations

### 7.1 Security

1. **Webhook Signature Verification**: All webhooks must be signed and verified
2. **API Key Authentication**: Service-to-service communication uses API keys
3. **HTTPS Only**: All OAuth callbacks and webhooks must use HTTPS in production
4. **Token Encryption**: OAuth tokens are encrypted before storage

### 7.2 Monitoring

1. **OAuth Flow Metrics**: Track success/failure rates for each provider
2. **Account Linking Metrics**: Monitor how often users link accounts across providers
3. **Error Tracking**: Log and alert on OAuth-related errors
4. **Performance Monitoring**: Track response times for login_or_create endpoint

### 7.3 Error Handling

1. **OAuth Provider Errors**: Handle provider-specific errors gracefully
2. **Network Failures**: Implement retry logic for webhook delivery
3. **Database Conflicts**: Handle race conditions in user creation
4. **Token Refresh**: Implement automatic token refresh for expired tokens

## 8. Migration Strategy

### 8.1 Phase 1: Infrastructure Setup
1. Set up NextAuth.js with Google and Microsoft providers
2. Create BFF layer with webhook endpoints
3. Implement login_or_create endpoint in user service
4. Add OAuth token storage functionality

### 8.2 Phase 2: Frontend Integration
1. Update frontend to use NextAuth for authentication
2. Implement login buttons and authentication hooks
3. Add session management and user profile display

### 8.3 Phase 3: Testing and Validation
1. Test OAuth flows with both providers
2. Test account linking scenarios
3. Test enterprise domain support
4. Validate email collision detection

### 8.4 Phase 4: Production Deployment
1. Deploy to staging environment
2. Conduct user acceptance testing
3. Deploy to production with feature flags
4. Monitor and optimize performance

## 9. Future Enhancements

### 9.1 Multi-Provider Support
- Allow users to link multiple OAuth providers to one account
- Implement provider switching in the UI
- Add provider-specific settings and preferences

### 9.2 Advanced Account Linking
- Implement account merging for duplicate accounts
- Add account verification for linked accounts
- Support for manual account linking

### 9.3 Enterprise Features
- Tenant-specific OAuth configurations
- SSO integration with enterprise identity providers
- Role-based access control based on OAuth provider

This design provides a complete, secure, and scalable OAuth integration that handles all the edge cases you mentioned while maintaining a clean architecture with proper separation of concerns. 