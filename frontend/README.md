# Briefly Frontend - NextAuth OAuth Integration

A Next.js frontend application with NextAuth.js integration for Google and Microsoft OAuth authentication, designed to work with the Briefly user service for granular OAuth permissions.

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm
- Running Briefly user service on `http://localhost:8001`
- OAuth credentials from Google and Microsoft (see setup below)

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env.local
   ```

3. **Configure environment variables** (see Environment Setup below)

4. **Start development server:**
   ```bash
   npm run dev
   ```

5. **Open in browser:**
   ```
   http://localhost:3000
   ```

## 🔧 Environment Setup

Create a `.env.local` file with the following variables:

```bash
# NextAuth Configuration
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-super-secret-key-here

# Google OAuth (for identity authentication)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft OAuth (for identity authentication)  
AZURE_AD_CLIENT_ID=your-azure-client-id
AZURE_AD_CLIENT_SECRET=your-azure-client-secret
AZURE_AD_TENANT_ID=common

# Backend Services
USER_SERVICE_URL=http://localhost:8001
API_FRONTEND_USER_KEY=your-api-key

# JWT Configuration (for development)
JWT_VERIFY_SIGNATURE=false

# Webhook Security
BFF_WEBHOOK_SECRET=your-webhook-secret
```

## 🔑 OAuth Provider Setup

### Google OAuth Setup

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create or select a project**
3. **Enable APIs:**
   - Google+ API (for basic profile)
   - Gmail API (for integration features)
   - Google Calendar API (for integration features)
4. **Create OAuth 2.0 credentials:**
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - `http://localhost:3000/api/auth/callback/google`
5. **Copy Client ID and Client Secret to your `.env.local`**

### Microsoft OAuth Setup

1. **Go to [Azure Portal](https://portal.azure.com/)**
2. **Navigate to Azure Active Directory → App registrations**
3. **Create new registration:**
   - Name: "Briefly Frontend"
   - Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
   - Redirect URI (Web): `http://localhost:3000/api/auth/callback/azure-ad`
4. **Configure API permissions:**
   - Microsoft Graph: `User.Read`, `offline_access`
5. **Create client secret:**
   - Go to "Certificates & secrets" → "New client secret"
6. **Copy Application (client) ID and client secret to your `.env.local`**

## 🏗️ Architecture Overview

### Three-Layer Architecture

This application implements a three-layer architecture with centralized authentication:

#### Layer 1: NextAuth BFF (Frontend)
- **Purpose:** User authentication and session management
- **Scopes:** Basic identity only (`openid`, `email`, `profile`)
- **Providers:** Google and Microsoft (Azure AD)
- **Flow:** User clicks "Sign in" → OAuth consent → JWT token generation

#### Layer 2: Express Gateway (API Gateway)
- **Purpose:** Centralized authentication, security, and request routing
- **Features:** JWT validation, rate limiting, malicious traffic filtering
- **Flow:** Frontend → Gateway → Backend services

#### Layer 3: Backend Services (Python)
- **Purpose:** Business logic and data management
- **Services:** Chat, User Management, Office Integrations
- **Flow:** Gateway → Backend with user context

### Benefits
- ✅ **Centralized authentication:** Single JWT token for all backend services
- ✅ **Enhanced security:** Gateway provides rate limiting and malicious traffic filtering
- ✅ **WebSocket/SSE support:** Real-time communication capabilities
- ✅ **Clean separation:** Frontend, gateway, and backend have distinct responsibilities
- ✅ **Scalable architecture:** Easy to migrate to managed API gateways later

## 📱 User Experience Flow

### 1. Initial Authentication
```
Visit app → Click "Sign in with Google/Microsoft" → OAuth consent → JWT token → Dashboard
```

### 2. API Communication
```
Frontend → Express Gateway (JWT validation) → Backend Services (User context)
```

### 3. Real-time Features
```
Chat: Frontend → Gateway → Chat Service (WebSocket/SSE)
Calendar: Frontend → Gateway → Office Service (Calendar data)
Email: Frontend → Gateway → Office Service (Email data)
```

### 4. Ongoing Usage
```
- JWT tokens automatically included in all API requests
- Gateway handles authentication and security
- Backend services receive user context automatically
```

## 🛠️ Available Scripts

- `npm run dev` - Start development server with turbopack
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## 📄 Key Pages & Components

### Pages
- `/` - Home page with app overview
- `/login` - OAuth provider selection and authentication
- `/dashboard` - Main authenticated dashboard with integration status
- `/profile` - User profile and account information
- `/integrations` - Integration management and OAuth flows
- `/onboarding` - Guided setup for new users

### Components
- `components/auth/oauth-buttons.tsx` - OAuth provider login buttons
- `components/auth/user-menu.tsx` - User menu with logout functionality
- `components/auth/session-provider.tsx` - NextAuth session wrapper
- `lib/api-client.ts` - Authenticated API client for user service
- `lib/auth.ts` - NextAuth configuration and utilities

## 🔒 Security Features

- **NextAuth.js:** Industry-standard authentication library
- **JWT tokens:** Secure session management
- **CSRF protection:** Built-in security against cross-site attacks
- **OAuth state validation:** Prevents authorization code attacks
- **API key authentication:** Secure communication with user service
- **Protected routes:** Middleware-based route protection

## 🌐 API Integration

### NextAuth Endpoints
- `GET/POST /api/auth/[...nextauth]` - NextAuth.js handler
- `POST /api/auth/webhook` - User service communication

### Express Gateway Integration
The frontend communicates with backend services through the gateway:
- **Chat Service**: `/api/chat` (POST), `/api/chat/stream` (SSE)
- **User Service**: `/api/users/me/*` (user management)
- **Office Service**: `/api/calendar/*`, `/api/email/*` (integrations)
- **WebSocket Support**: `ws://gateway/api/chat/ws`

### Authentication Flow
1. NextAuth generates JWT tokens with user context
2. Frontend includes JWT in Authorization header
3. Gateway validates JWT and forwards user context
4. Backend services receive authenticated requests

## 🚨 Troubleshooting

### Common Issues

**NextAuth Configuration Errors:**
```bash
Error: Please define a `NEXTAUTH_SECRET` environment variable
```
**Solution:** Add `NEXTAUTH_SECRET` to your `.env.local`

**OAuth Redirect URI Mismatch:**
```bash
Error: redirect_uri_mismatch
```
**Solution:** Verify redirect URIs in OAuth provider console match exactly

**User Service Connection Issues:**
```bash
Error: Failed to create/update user
```
**Solution:** Ensure user service is running and `USER_SERVICE_URL` is correct

**Missing Dependencies:**
```bash
Error: Cannot find module 'next-auth'
```
**Solution:** Run `npm install` to install NextAuth.js

### Development Tips

1. **Use browser dev tools** to debug OAuth flows
2. **Check user service logs** for integration issues
3. **Verify environment variables** are loaded correctly
4. **Test with incognito mode** to simulate new user experience

## 🎯 Demo Scenarios

### Complete OAuth Flow Demo
1. Start user service: `cd services/user && ./start.sh`
2. Start frontend: `npm run dev`
3. Visit `http://localhost:3000`
4. Click "Sign in with Google"
5. Complete OAuth consent
6. Go to "Integrations" page
7. Connect Google Calendar with specific scopes
8. View integration status in dashboard

### Integration Management Demo
1. Connect multiple providers (Google + Microsoft)
2. View real-time integration health
3. Disconnect and reconnect services
4. Test token refresh functionality
5. Explore granular permission control

## 📚 Related Documentation

- [NextAuth.js Documentation](https://next-auth.js.org/)
- [Briefly User Service](../services/user/README.md)
- [OAuth BFF Integration Design](../documentation/oauth-bff-integration-design.md)
- [Enterprise OAuth Design](../documentation/enterprise-oauth-design.md)

## 🔄 Development Workflow

1. **Make changes** to components or pages
2. **Test authentication flows** in browser
3. **Verify integration** with user service
4. **Check console logs** for errors
5. **Test mobile responsiveness**
6. **Validate security considerations**

This frontend application showcases the complete OAuth integration capabilities of the Briefly platform, providing a polished user experience for authentication and granular integration management.
