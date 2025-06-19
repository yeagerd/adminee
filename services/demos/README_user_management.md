# User Management Service Demo

This demo showcases the comprehensive functionality of the user management service, including user profiles, preferences, OAuth integrations, and service-to-service APIs.

## Optional Prerequisites (for full OAuth demo)

- Google OAuth credentials configured
- Microsoft OAuth credentials configured
- Valid redirect URIs set up

## Usage

The demo supports two modes:

### Interactive Mode (Default)
Full demo with OAuth menu and browser-based flows:
```bash
python user_management_demo.py
```

### Simple Mode
Non-interactive demo that tests all core functionality without OAuth completion:
```bash
python user_management_demo.py --simple
```

### Custom Service URL
Point to a different service instance:
```bash
python user_management_demo.py --base-url http://your-service.com:8080
python user_management_demo.py --simple --base-url http://your-service.com:8080
```

### Help
View all available options:
```bash
python user_management_demo.py --help
```

## Quick Start

### 1. Start the User Management Service

```bash
# Terminal 1: Start the service (from project root)
cd /Users/yeagerd/github/briefly/services/user
alembic upgrade head
export JWT_VERIFY_SIGNATURE=false
export TOKEN_ENCRYPTION_SALT="ZGVtby1lbmNyeXB0aW9uLXNhbHQtZm9yLXRlc3Rpbmc="
cd /Users/yeagerd/github/briefly  # Navigate to project root
uvicorn services.user.main:app --reload --port 8001
```

Wait for the service to start and show:
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
```

### 2. Run the Demo

Choose your preferred mode:

**Quick Test (Simple Mode):**
```bash
# Terminal 2: Run simple demo
cd services/demos
python user_management_demo.py --simple
```

**Full Interactive Demo:**
```bash
# Terminal 2: Run interactive demo
cd services/demos
python user_management_demo.py
```

## Demo Modes

### Simple Mode (`--simple`)

Non-interactive demo that runs all core functionality sequentially:

1. **Service Health Checks** - Verifies service is running and ready
2. **User Profile Demo** - Creates and manages user profiles
3. **Preferences Management** - Updates various preference categories
4. **Integration Listing** - Shows current OAuth integrations
5. **OAuth Flow Initiation** - Tests OAuth flow start (without completion)
6. **Internal API Testing** - Tests service-to-service authentication

**Sample Simple Mode Output:**
```bash
🎯 User Management Service Demo
================================

Running in SIMPLE mode (non-interactive)

This demo requires:
• User management service running on http://localhost:8001

============================================================
 User Management Service Simple Demo
============================================================

This simple demo showcases core user management functionality:
• Health and readiness checks
• User profile management
• User preferences
• Integration listing
• OAuth flow initiation (without completion)
• Service-to-service API

--- Service Health Check ---
🟢 200 OK
   Health check
   Response: {
     "status": "healthy",
     "service": "user-management"
   }

✅ Demo completed successfully!
📋 All core functionality tested:
   - Service health: ✅
   - User creation: ✅
   - Profile operations: ✅
   - Preferences: ✅
   - Integrations: ✅
   - OAuth initiation: ✅
   - Internal API: ✅

💡 For interactive OAuth flows, run without --simple flag
```

### Interactive Mode (Default)

Full-featured demo with OAuth menu and real browser-based authorization:

1. **Service Health Checks** - Same as simple mode
2. **User Profile Demo** - Same as simple mode  
3. **Preferences Management** - Same as simple mode
4. **OAuth Integration Menu** - Interactive menu for OAuth flows:
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

**OAuth Flow Demo (Interactive Mode Only):**

When you select an OAuth provider:

1. **Authorization URL Generation** - Creates secure OAuth state with PKCE
2. **Browser Authorization** - Opens browser for real OAuth consent
3. **Token Exchange** - Exchanges authorization code for tokens
4. **Integration Management** - View, refresh, test, and disconnect integrations

## Sample Output

### Simple Mode
```bash
🎯 User Management Service Demo
================================

Running in SIMPLE mode (non-interactive)

============================================================
 User Management Service Simple Demo
============================================================

--- Service Health Check ---
🟢 200 OK
   Health check

--- Creating Demo User via Webhook ---
🟢 200 OK
   Demo user creation via webhook

--- Getting User Profile ---
🟢 200 OK
   User profile retrieval

--- Testing OAuth Flow Initiation ---
🟢 200 OK
   OAuth flow started successfully
   State: secure_random_state_12345

============================================================
 Simple Demo Summary
============================================================
✅ Demo completed successfully!
```

### Interactive Mode
```bash
🎯 User Management Service Demo
================================

Running in INTERACTIVE mode

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
🌐 Opening browser for Google OAuth authorization...
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
DB_URL_USER=postgresql://user:pass@localhost/briefly_user_mgmt
CLERK_SECRET_KEY=your_clerk_secret_key
TOKEN_ENCRYPTION_SALT=your_encryption_salt
```

### OAuth Provider Setup

#### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add redirect URI: `http://localhost:8001/oauth/callback`

#### Microsoft OAuth Setup
1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application in Azure AD
3. Configure redirect URI: `http://localhost:8001/oauth/callback`
4. Note the Application ID and secret

## Troubleshooting

### Service Not Running
```bash
🔴 Service not available: Connection refused
```
**Solution:** Start the user management service first

### OAuth Flow Issues
```bash
🔴 Failed to start OAuth flow: OAuth credentials not configured
```
**Solution:** Configure OAuth credentials in environment variables or skip OAuth demo.

### Database Connection Issues
```bash
🔴 503 Service Unavailable - Database not connected
```
**Solution:** Ensure PostgreSQL is running and DB_URL_USER is configured correctly.

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
- [API Reference](http://localhost:8001/docs) (when service is running)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs for detailed error information
3. Verify all prerequisites are met
4. Ensure OAuth credentials are properly configured 