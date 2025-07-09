# NextAuth Testing with Briefly Demo

This guide shows you how to test NextAuth authentication flows alongside the existing Clerk setup using the enhanced chat demo.

## Overview

The NextAuth testing setup allows you to:
- Test real Google/Microsoft OAuth flows
- Compare NextAuth vs Clerk authentication approaches
- See how NextAuth would work with Briefly services
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

### Scenario 1: Compare Authentication Approaches

1. **Test Clerk Authentication:**
   ```
   auth
   ```
   Follow the prompts to set up Clerk authentication.

2. **Test NextAuth Authentication:**
   ```
   nextauth google
   ```
   This will:
   - Open your browser to Google OAuth
   - Show you the NextAuth JWT token after authentication
   - Store the token for comparison

3. **Compare the Approaches:**
   ```
   compare
   ```
   This shows a side-by-side comparison of Clerk vs NextAuth tokens.

### Scenario 2: NextAuth-Only Testing

Run the demo in NextAuth-only mode:

```bash
python services/demos/chat_nextauth.py --nextauth-only
```

This skips Clerk setup and focuses on NextAuth testing.

### Scenario 3: Quick Comparison Demo

```bash
python services/demos/chat_nextauth.py --compare
```

This creates demo tokens and shows the architectural differences.

## Available Commands

### NextAuth-Specific Commands

- `nextauth google` - Test NextAuth with Google OAuth
- `nextauth microsoft` - Test NextAuth with Microsoft OAuth  
- `compare` - Compare Clerk vs NextAuth tokens
- `demo-nextauth` - Run full NextAuth integration demonstration

### Original Commands

All original chat demo commands work:
- `auth` - Clerk authentication
- `oauth google` - Clerk OAuth setup
- Chat functionality, draft management, etc.

## What You'll See

### NextAuth OAuth Flow

1. **Authorization URL:** The demo opens your browser to Google/Microsoft
2. **OAuth Consent:** You approve access to your calendar/email
3. **Success Page:** Shows your NextAuth JWT token with embedded OAuth tokens
4. **Token Analysis:** The demo decodes and analyzes the token structure

### Token Comparison

The comparison shows key differences:

| Field | Clerk | NextAuth |
|-------|-------|----------|
| User ID | `user_123` | `google_456` |
| Provider | Not included | `google` |
| Access Token | Stored separately | Embedded in JWT |
| OAuth Setup | Separate step | Combined with login |

### Architecture Insights

The demo highlights how NextAuth would:
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

## Key Benefits Demonstrated

### Current Clerk Approach
```
User → Clerk Login → App → "Connect Google" → OAuth → Separate Token Storage
```

### NextAuth Approach
```
User → NextAuth (Google/Microsoft) → App + Tokens (Done!)
```

### Advantages Shown

1. **Single Login Flow:** One step instead of two
2. **Better UX:** No "connect your calendar" step needed
3. **Embedded Tokens:** OAuth tokens included in JWT
4. **Provider Context:** JWT includes which provider was used
5. **Simplified Architecture:** Fewer moving parts

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

1. **Evaluate the UX:** Compare the user experience of both approaches
2. **Assess Complexity:** Consider the architectural trade-offs
3. **Plan Migration:** Use insights to plan a potential NextAuth migration
4. **Prototype Integration:** Extend the test server for your specific needs

The testing setup provides a realistic preview of how NextAuth would work with Briefly, helping you make an informed decision about authentication architecture. 