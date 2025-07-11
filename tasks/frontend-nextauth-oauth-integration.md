# Frontend NextAuth OAuth Integration Task List

## Overview

This task list outlines building a complete frontend NextAuth integration with the existing user service OAuth capabilities. The goal is to create a working browser demo that demonstrates the full OAuth dance from frontend login to backend service integration.

## Current State Assessment

### ✅ Already Built
- **User Service**: Complete OAuth integration service with Google/Microsoft support
- **OAuth Flow Management**: Token storage, encryption, refresh, and webhook support
- **Backend API Endpoints**: Full integration CRUD with `/oauth/start` and `/oauth/callback`
- **Demo Infrastructure**: Working command-line OAuth demos
- **Documentation**: Comprehensive OAuth BFF integration design

### ❌ Missing for Frontend Demo
- NextAuth.js setup and configuration
- Frontend authentication UI/UX
- API route handlers for OAuth webhooks
- Session management and protected routes
- Integration with existing user service

## Task Breakdown

### Phase 1: Foundation Setup

#### 1. NextAuth.js Dependencies and Configuration
**Files**: `frontend/package.json`, `frontend/.env.local`
- Install NextAuth.js and required providers
- Add `next-auth` and OAuth provider packages
- Set up environment variables for OAuth credentials
- Configure base NextAuth settings

#### 2. NextAuth API Routes (Identity Only)
**Files**: `frontend/app/api/auth/[...nextauth]/route.ts`
- Create NextAuth API route handler for **authentication only**
- Configure Google OAuth provider with basic identity scopes:
  - `openid`, `email`, `profile` (identity only)
- Configure Microsoft OAuth provider with basic scopes:
  - `openid`, `email`, `profile` (identity only)
- Set up JWT and session callbacks to store user identity
- Configure redirect URLs for identity authentication
- **Note**: Integration scopes (calendar, email) handled separately via user service

#### 3. OAuth Webhook Handler
**Files**: `frontend/app/api/auth/webhook/route.ts`
- Create webhook endpoint to communicate with user service
- Implement webhook authentication/security
- Handle user creation/update via user service API
- Process OAuth token storage through user service integration endpoints
- Handle error cases and retries

### Phase 2: Session and Auth Management

#### 4. SessionProvider Setup
**Files**: `frontend/app/layout.tsx`, `frontend/lib/auth.ts`
- Wrap app with NextAuth SessionProvider
- Create auth configuration utilities
- Set up session type definitions with OAuth token data
- Configure session persistence and refresh logic

#### 5. Authentication Middleware
**Files**: `frontend/middleware.ts`
- Implement NextAuth middleware for route protection
- Define protected route patterns
- Handle authentication redirects
- Add session validation logic

#### 6. API Client with Auth
**Files**: `frontend/lib/api-client.ts`
- Create authenticated API client for user service calls
- Implement token refresh logic using NextAuth session
- Add request/response interceptors for authentication
- Handle API errors and auth failures gracefully

### Phase 3: UI Components

#### 7. Login/Logout Components
**Files**: `frontend/components/auth/`, `frontend/app/login/page.tsx`
- Create OAuth provider buttons (Google, Microsoft)
- Design login page with provider selection
- Implement logout functionality
- Add loading states and error handling
- Style with existing UI system (shadcn/ui)

#### 8. Navbar Authentication Integration
**Files**: `frontend/components/navbar.tsx`
- Add user avatar and session display
- Implement logout dropdown/button
- Show authentication status
- Handle unauthenticated state

#### 9. User Profile Page
**Files**: `frontend/app/profile/page.tsx`, `frontend/components/profile/`
- Display user information from NextAuth session
- Show OAuth provider details
- List connected integrations status
- Provide integration management controls

### Phase 4: OAuth Integration UI

#### 10. OAuth Integration Management (Using User Service APIs)
**Files**: `frontend/components/integrations/`, `frontend/app/integrations/page.tsx`
- Create integration status dashboard using existing user service endpoints
- Connect integrations via `POST /users/{user_id}/integrations/oauth/start`:
  - Google: `gmail.readonly`, `calendar` scopes
  - Microsoft: `User.Read`, `Calendars.ReadWrite`, `Mail.Read` scopes
- Handle OAuth callbacks via user service `POST /oauth/callback` endpoint
- Display integration status from `GET /users/{user_id}/integrations`
- Add connect/disconnect functionality leveraging user service OAuth management
- Display token expiration and health status from user service data

#### 11. Integration Status Components
**Files**: `frontend/components/integrations/status-card.tsx`
- Show real-time integration health
- Display last sync times and token validity
- Add refresh token functionality
- Handle integration errors and reconnection

#### 12. Onboarding OAuth Flow
**Files**: `frontend/app/(onboarding)/onboarding/page.tsx`
- Replace mock calendar connection with real OAuth
- Guide users through Google/Microsoft setup
- Handle OAuth callback within onboarding flow
- Add progress indicators and success states

### Phase 5: Protected Routes and Dashboard

#### 13. Protected Dashboard
**Files**: `frontend/app/dashboard/page.tsx`
- Create main authenticated dashboard
- Require valid session for access
- Display integration status summary
- Show connected services and capabilities

#### 14. Route Protection Implementation
**Files**: `frontend/middleware.ts`, `frontend/lib/auth-utils.ts`
- Protect `/dashboard`, `/profile`, `/integrations` routes
- Redirect unauthenticated users to login
- Handle session expiration gracefully
- Implement proper loading states

### Phase 6: Error Handling and Polish

#### 15. Comprehensive Error Handling
**Files**: `frontend/components/ui/error-boundary.tsx`, `frontend/lib/error-handling.ts`
- Add OAuth-specific error handling
- Handle network failures gracefully
- Display user-friendly error messages
- Implement retry mechanisms for failed requests

#### 16. Loading States and UX
**Files**: `frontend/components/ui/loading-states.tsx`
- Add loading spinners for OAuth flows
- Implement skeleton screens for integration status
- Add progress indicators for multi-step OAuth setup
- Handle slow network conditions

### Phase 7: Testing and Demo Setup

#### 17. Demo Environment Configuration
**Files**: `frontend/.env.example`, `frontend/README.md`
- Set up development OAuth applications
- Create test user accounts
- Configure local development URLs
- Document OAuth credential setup process

#### 18. End-to-End Demo Testing
**Files**: `frontend/tests/`, demo scripts
- Test complete OAuth flow: login → integration → logout
- Verify token storage and refresh
- Test error scenarios (expired tokens, revoked access)
- Validate integration with user service APIs

#### 19. Documentation and Setup Guide
**Files**: `frontend/README.md`, `docs/oauth-setup.md`
- Document OAuth provider setup (Google Cloud Console, Azure Portal)
- Create step-by-step demo setup instructions
- Add troubleshooting guide for common issues
- Document environment variable requirements

## Environment Variables Required

```bash
# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft OAuth
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_CLIENT_SECRET=your-azure-client-secret
AZURE_AD_TENANT_ID=common

# Backend Services
USER_SERVICE_URL=http://localhost:8001
USER_SERVICE_API_KEY=your-api-key
BFF_WEBHOOK_SECRET=your-webhook-secret
```

## Success Criteria

### Minimum Viable Demo
- [ ] User can click "Sign in with Google/Microsoft" 
- [ ] OAuth flow completes successfully in browser
- [ ] User session is established with NextAuth
- [ ] User profile shows connected provider information
- [ ] Integration status displays in dashboard

### Full Featured Demo
- [ ] Complete onboarding flow with OAuth setup
- [ ] Integration management (connect/disconnect providers)
- [ ] Token refresh and error handling
- [ ] Protected routes and session management
- [ ] Real-time integration status and health monitoring

### Technical Integration
- [ ] Frontend communicates with user service via authenticated APIs
- [ ] OAuth tokens stored securely in user service
- [ ] Session persistence across browser refreshes
- [ ] Proper error handling and user feedback
- [ ] Mobile-responsive OAuth flows

## Architecture Flow - Two-Step OAuth

### Step 1: Identity Authentication (NextAuth)
```
Browser → "Sign in with Google" → NextAuth → Google (identity scopes) → 
Session Created → User Dashboard
```

### Step 2: Granular Integration Setup (User Service)
```
Dashboard → "Connect Calendar" → User Service OAuth API → Google (calendar scopes) → 
OAuth Callback → Token Storage → Integration Active
```

### Complete Architecture
```
NextAuth (Identity) + User Service (Integrations) = Full OAuth Experience
    ↓                           ↓
Browser Session          Granular Permissions
Basic Profile            Calendar, Email, etc.
```

**Benefits**:
- Users connect identity first, then choose specific integrations
- Leverages existing robust user service OAuth infrastructure  
- Granular permission control per integration
- Better user experience with progressive consent

## User Experience Flow

### 1. Initial Authentication
- User visits Briefly app (unauthenticated)
- Clicks "Sign in with Google" or "Sign in with Microsoft"
- **NextAuth handles**: Basic identity consent (name, email, profile)
- User returns to app with authenticated session

### 2. Integration Setup (Optional & Granular)
- User sees dashboard with integration options
- Clicks "Connect Google Calendar" → User service OAuth with calendar scopes
- Clicks "Connect Gmail" → User service OAuth with email scopes  
- Clicks "Connect Microsoft Calendar" → User service OAuth with different scopes
- Each integration is independent and optional

### 3. Ongoing Usage
- User has authenticated session via NextAuth
- App can access calendar/email via user service integration tokens
- User can disconnect individual integrations without losing identity session
- User can add new integrations anytime

This creates a complete browser-based demo of the OAuth integration system, showcasing the full power of the existing backend OAuth infrastructure through a polished frontend experience. 