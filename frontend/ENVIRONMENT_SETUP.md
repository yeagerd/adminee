# Unified Authentication Patterns (Summary)

- **User-facing endpoints:**
  - Use NextAuth JWT authentication (user logs in via OAuth, receives JWT)
  - JWT is attached as a Bearer token in the Authorization header for all API calls
  - Endpoints use `/me` or header-based user extraction (no user_id in path/query)

- **Service-to-service and background jobs:**
  - Use API key authentication (API key in `X-API-Key` or `Authorization` header)
  - Internal endpoints use `/internal` prefix and require API key
  - API keys are stored in environment variables and must **never** be exposed to client-side code

- **Environment variables:**
  - `NEXTAUTH_SECRET`: Used to sign/validate JWTs (must match between frontend, gateway, and backend)
  - `API_FRONTEND_USER_KEY`, `API_FRONTEND_CHAT_KEY`, `API_FRONTEND_OFFICE_KEY`: API keys for service-to-service auth (server-side only)
  - `NEXT_PUBLIC_GATEWAY_URL`: Used by frontend to call the gateway

---

# Frontend Environment Setup

This document describes the environment variables required for the frontend application.

## Required Environment Variables

Create a `.env.local` file in the frontend directory with the following variables:

### NextAuth Configuration
```bash
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret-here
```

### Gateway URL (for client-side API calls)
```bash
NEXT_PUBLIC_GATEWAY_URL=http://localhost:3001
```

### Service URLs (for server-side use)
```bash
CHAT_SERVICE_URL=http://localhost:8001
USER_SERVICE_URL=http://localhost:8000
OFFICE_SERVICE_URL=http://localhost:8002
```

### API Keys for Service-to-Service Communication
```bash
API_FRONTEND_CHAT_KEY=test-FRONTEND_CHAT_KEY
API_FRONTEND_USER_KEY=test-FRONTEND_USER_KEY
API_FRONTEND_OFFICE_KEY=test-FRONTEND_OFFICE_KEY
API_FRONTEND_CHAT_KEY=test-FRONTEND_CHAT_KEY
```

### OAuth Configuration (Microsoft Entra ID / Azure AD)
```bash
AZURE_AD_CLIENT_ID=your-azure-ad-client-id
AZURE_AD_CLIENT_SECRET=your-azure-ad-client-secret
AZURE_AD_TENANT_ID=your-azure-ad-tenant-id
```

### Webhook Secret (for OAuth callbacks)
```bash
BFF_WEBHOOK_SECRET=your-webhook-secret-here
```

## Environment Validation

The frontend uses granular environment validation:

- **Chat API Route**: Validates `API_CHAT_USER_KEY`
- **User API Route**: Validates `API_FRONTEND_USER_KEY`
- **Webhook Route**: Validates `API_FRONTEND_USER_KEY`
- **Integrations Route**: No validation needed (uses NextAuth tokens)

## Development Setup

1. Copy the example environment variables above
2. Create `.env.local` in the frontend directory
3. Fill in your actual values
4. Run `npm run dev` to start the development server

## Production Setup

For production, ensure all environment variables are properly set in your deployment environment. The application will validate required variables at startup and provide clear error messages for missing configuration. 