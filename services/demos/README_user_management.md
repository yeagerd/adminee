# User Management Service Demo

This demo showcases the comprehensive functionality of the user management service, including user profiles, preferences, OAuth integrations, and service-to-service APIs.

## Features Demonstrated

### 🏥 Health & Status
- Service health checks (`/health`)
- Service readiness checks (`/ready`)
- Real-time service monitoring

### 👤 User Profile Management
- User creation via webhook simulation
- Profile retrieval and updates
- User data management
- Audit logging of profile changes

### ⚙️ User Preferences
- Complete preference management
- UI preferences (theme, language, timezone)
- Notification preferences
- AI preferences and consent
- Partial preference updates

### 🔗 OAuth Integrations
- **Google OAuth Integration**
  - Complete OAuth 2.0 flow with PKCE
  - Real browser-based authorization
  - Token management and refresh
  - Scope validation
  
- **Microsoft OAuth Integration**
  - Microsoft Graph API integration
  - Enterprise-grade OAuth flow
  - Token lifecycle management
  
- **Integration Management**
  - List all user integrations
  - Check integration status and health
  - Refresh expired tokens
  - Disconnect integrations

### 🔐 Service-to-Service API
- Internal token retrieval
- Automatic token refresh
- Scope validation
- Service authentication

### 🛡️ Security Features
- JWT authentication simulation
- API key authentication
- Input validation and sanitization
- Error handling and recovery

## Prerequisites

### Required
- Python 3.9+
- User Management Service running
- Web browser for OAuth flows

### Optional (for full OAuth demo)
- Google OAuth credentials configured
- Microsoft OAuth credentials configured
- Valid redirect URIs set up

## Quick Start

### 1. Start the User Management Service

```bash
# Terminal 1: Start the service (from project root)
cd /Users/yeagerd/github/briefly/services/user_management
alembic upgrade head
export DATABASE_URL="sqlite:///./services/user_management/user_management.db"
cd /path/to/briefly  # Navigate to project root
uvicorn services.user_management.main:app --reload --port 8000
```

Wait for the service to start and show:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### 2. Run the Demo

```bash
# Terminal 2: Run the demo
cd services/demos
python user_management_demo.py
```

## Demo Flow

### Interactive Mode

The demo runs in interactive mode, allowing you to:

1. **Service Health Check**
   - Verifies service is running and healthy
   - Checks database connectivity
   - Validates service readiness

2. **User Profile Demo**
   - Creates a demo user via webhook simulation
   - Retrieves and displays user profile
   - Updates profile information
   - Shows audit logging in action

3. **Preferences Management**
   - Displays default user preferences
   - Updates various preference categories
   - Demonstrates partial updates
   - Shows preference validation

4. **OAuth Integration Menu**
   ```
   OAuth Integration Demo
   1. Connect Google Integration
   2. Connect Microsoft Integration
   3. View Integration Status
   4. Refresh Integration Token
   5. Test Internal API
   6. Disconnect Integration
   7. Skip OAuth Demo
   0. Exit Demo
   ```

### OAuth Flow Demo

When you select an OAuth provider:

1. **Authorization URL Generation**
   - Creates secure OAuth state with PKCE
   - Generates authorization URL with proper scopes
   - Opens browser automatically

2. **Browser Authorization**
   - Redirects to provider's OAuth consent screen
   - User grants permissions
   - Provider redirects back with authorization code

3. **Token Exchange**
   - Exchanges authorization code for tokens
   - Stores encrypted tokens securely
   - Creates integration record

4. **Integration Management**
   - View integration status
   - Refresh tokens
   - Test token validity
   - Disconnect when done

## Sample Output

```bash
🎯 User Management Service Demo
================================

This demo requires:
• User management service running on http://localhost:8000
• Valid OAuth credentials (optional for OAuth demo)
• Web browser for OAuth flows

============================================================
 User Management Service Interactive Demo
============================================================

--- Service Health Check ---
🟢 200 OK
   Health check
   Response: {
     "status": "healthy",
     "service": "user-management",
     "version": "0.1.0",
     "timestamp": "2024-01-01T12:00:00Z",
     "environment": "development",
     "database": {"status": "healthy"}
   }

--- Creating Demo User via Webhook ---
🟢 200 OK
   Demo user creation via webhook
   Response: {
     "message": "User created successfully",
     "user_id": "demo_user_12345"
   }

--- Getting User Profile ---
🟢 200 OK
   User profile retrieval
   Response: {
     "id": "demo_user_12345",
     "email": "demo.user@example.com",
     "first_name": "Demo",
     "last_name": "User",
     "profile_image_url": "https://images.clerk.dev/demo-avatar.png",
     "created_at": "2024-01-01T12:00:00Z"
   }

🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗
OAuth Integration Demo
🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗🔗
1. Connect Google Integration
2. Connect Microsoft Integration
3. View Integration Status
4. Refresh Integration Token
5. Test Internal API
6. Disconnect Integration
7. Skip OAuth Demo
0. Exit Demo

Enter your choice (0-7): 1

🚀 Starting Google OAuth Demo
This will open your browser for OAuth authorization.
Note: You'll need valid OAuth credentials configured for this to work.

Do you want to proceed with Google OAuth? (y/n): y

--- Starting OAuth Flow for Google ---
🟢 200 OK
   OAuth flow started successfully
   Authorization URL: https://accounts.google.com/oauth2/v2/auth?client_id=...
   State: secure_random_state_12345

🌐 Opening browser for Google OAuth authorization...
   Please complete the OAuth flow in your browser.
   After authorization, you'll be redirected back to the service.

Press Enter after completing the Google OAuth flow...
```

## Configuration

### Environment Variables

For full OAuth functionality, configure these environment variables:

```bash
# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Microsoft OAuth (optional)
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret

# Service Configuration
DATABASE_URL=postgresql://user:pass@localhost/briefly_user_mgmt
CLERK_SECRET_KEY=your_clerk_secret_key
ENCRYPTION_SERVICE_SALT=your_encryption_salt
```

### OAuth Provider Setup

#### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add redirect URI: `http://localhost:8000/oauth/callback`

#### Microsoft OAuth Setup
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application in Azure AD
3. Configure redirect URI: `http://localhost:8000/oauth/callback`
4. Note the Application ID and secret

## Troubleshooting

### Service Not Running
```bash
🔴 Service not available: Connection refused
```
**Solution:** Start the user management service first:
```bash
# From project root directory
cd /path/to/briefly
uvicorn services.user_management.main:app --reload --port 8000
```

### OAuth Flow Issues
```bash
🔴 Failed to start OAuth flow: OAuth credentials not configured
```
**Solution:** Configure OAuth credentials in environment variables or skip OAuth demo.

### Database Connection Issues
```bash
🔴 503 Service Unavailable - Database not connected
```
**Solution:** Ensure PostgreSQL is running and DATABASE_URL is configured correctly.

### Permission Errors
```bash
🔴 403 Forbidden - Authentication failed
```
**Solution:** The demo uses mock JWT tokens. In production, you'd need valid Clerk JWT tokens.

## Security Notes

⚠️ **Demo Limitations:**
- Uses mock JWT tokens for authentication
- Uses demo webhook signatures
- OAuth credentials should be kept secure
- Not intended for production use

🔒 **Security Features Demonstrated:**
- Token encryption and secure storage
- PKCE for OAuth security
- Input validation and sanitization
- Audit logging for compliance
- Service-to-service authentication

## Advanced Usage

### Custom Configuration

You can customize the demo by modifying the `UserManagementDemo` class:

```python
# Use different base URL
demo = UserManagementDemo(base_url="https://your-api.com")

# Use different user ID
demo.demo_user_id = "your_user_id"

# Use different service credentials
demo.service_api_key = "your_service_key"
```

### Running Specific Demo Sections

```python
async with UserManagementDemo() as demo:
    # Only test health endpoints
    await demo.check_service_health()
    await demo.check_service_readiness()
    
    # Only test user management
    await demo.create_demo_user()
    await demo.get_user_profile()
    
    # Only test OAuth for specific provider
    await demo.demo_oauth_flow("google")
```

## Related Documentation

- [User Management Service Documentation](../../documentation/user-management-service.md)
- [OAuth Integration Guide](../user_management/integrations/README.md)
- [API Reference](http://localhost:8000/docs) (when service is running)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs for detailed error information
3. Verify all prerequisites are met
4. Ensure OAuth credentials are properly configured 