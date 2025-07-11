# NextAuth Testing with Briefly Demo

This guide shows you how to test NextAuth authentication flows using the enhanced chat demo.

## Overview

The NextAuth testing setup allows you to:
- Test real Google/Microsoft OAuth flows
- See how NextAuth works with Briefly services
- Experience the simplified single-login flow

## Quick Start

### 1. Install Dependencies

Make sure you have the required packages:

```bash
pip install fastapi uvicorn httpx pyjwt python-multipart
```

### 2. Set Up OAuth Credentials (Optional)

For real OAuth testing, set up your OAuth applications:

**Google OAuth:**
```bash
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
```

**Microsoft OAuth:**
```bash
export MICROSOFT_CLIENT_ID="your-microsoft-client-id"
export MICROSOFT_CLIENT_SECRET="your-microsoft-client-secret"
```

**Note:** You can test without real credentials - the demo will show you the OAuth URLs and simulate the flow.

### 3. Start the NextAuth Test Server

In one terminal:

```bash
python services/demos/nextauth_test_server.py
```

This starts a test server on `http://localhost:8090` that simulates NextAuth functionality.

### 4. Run the Enhanced Demo

In another terminal:

```bash
python services/demos/chat_nextauth.py
```

## Testing Scenarios

### Test NextAuth Authentication:
   ```
   nextauth google
   ```
   This will:
   - Open your browser to Google OAuth
   - Show you the NextAuth JWT token after authentication

### Run the Demo with NextAuth:

```bash
python services/demos/chat_nextauth.py
```

## Available Commands

### NextAuth-Specific Commands

- `nextauth google` - Test NextAuth with Google OAuth
- `nextauth microsoft` - Test NextAuth with Microsoft OAuth  
- `demo-nextauth` - Run full NextAuth integration demonstration

### Original Commands

All original chat demo commands work:
- Chat functionality, draft management, etc.

## What You'll See

### NextAuth OAuth Flow

1. **Authorization URL:** The demo opens your browser to Google/Microsoft
2. **OAuth Consent:** You approve access to your calendar/email
3. **Success Page:** Shows your NextAuth JWT token with embedded OAuth tokens
4. **Token Analysis:** The demo decodes and analyzes the token structure

### Token Structure

The NextAuth JWT token contains the following key information:

| Field | Example Value | Description |
|-------|---------------|-------------|
| User ID | `google_456` | The unique ID for the user from the OAuth provider. |
| Provider | `google` | The OAuth provider used for authentication (e.g., google, microsoft). |
| Access Token | (embedded) | The OAuth access token from the provider. |
| Scopes | `openid email profile https://www.googleapis.com/auth/calendar` | The permissions granted by the user. |

### Architecture Insights

The demo highlights how NextAuth:
- ✅ Combine authentication + OAuth in one step
- ✅ Include OAuth tokens directly in the JWT
- ✅ Eliminate the need for separate OAuth setup
- ✅ Reduce frontend complexity

## Real OAuth Testing

### With Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable Google+ API
3. Create OAuth 2.0 credentials
4. Add `http://localhost:8090/auth/oauth/callback/google` as a redirect URI
5. Set the environment variables and test

### With Microsoft OAuth

1. Go to [Azure App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps)
2. Register a new application
3. Add `http://localhost:8090/auth/oauth/callback/microsoft` as a redirect URI
4. Create a client secret
5. Set the environment variables and test

## Key Benefits of NextAuth

### NextAuth Approach
```
User → NextAuth (Google/Microsoft) → App + Tokens (Done!)
```

### Advantages

1. **Single Login Flow:** Authentication and OAuth token retrieval happen in a single step.
2. **Better UX:** Users don't need a separate step to "connect their calendar" or other services.
3. **Embedded Tokens:** OAuth access tokens are embedded directly within the NextAuth JWT.
4. **Provider Context:** The JWT includes information about which OAuth provider was used (e.g., Google, Microsoft).
5. **Simplified Architecture:** This approach reduces the number of moving parts in the authentication system.

## Troubleshooting

### NextAuth Server Not Available
```
❌ NextAuth test server not available
   Start it with: python services/demos/nextauth_test_server.py
```

**Solution:** Start the NextAuth test server in a separate terminal.

### OAuth Credentials Not Set
The demo works without real OAuth credentials - it will show you the OAuth URLs and let you simulate the flow.

### Import Errors
```
❌ NextAuth utilities not available
```

**Solution:** Make sure all dependencies are installed:
```bash
pip install fastapi uvicorn httpx pyjwt python-multipart
```

## Next Steps

After testing, you can:

1. **Evaluate the UX:** Observe the streamlined user experience with NextAuth.
2. **Assess Complexity:** Note the simplified architecture.
3. **Prototype Integration:** Extend the test server for any specific needs or further exploration.

This testing setup provides a realistic preview of how NextAuth works with Briefly.