# Office Service Full Integration Demo

This demo shows the complete Office Service integration by making HTTP requests to a running Office Service instance. It demonstrates the full production workflow including unified API responses, error handling, and provider integration health checks.

## Comparison with `office.py`

| Feature | `office.py` | `office_full.py` |
|---------|-------------|------------------|
| **Architecture** | Direct API client calls | HTTP requests to Office Service |
| **Dependencies** | Office Service components | Running Office Service + HTTP client |
| **Use Case** | Test API clients & normalizers | Test complete service integration |
| **Realism** | Component-level testing | Production-like API usage |
| **Token Management** | Direct environment variables | Demo token manager in service |

## Prerequisites

### 1. Install Dependencies

The full demo requires `httpx` for making HTTP requests (already included in requirements.txt).

### 2. Get API Tokens 

Follow the same process as `office.py` to get your Google and Microsoft tokens:
- **Google**: OAuth 2.0 tokens with Gmail, Calendar, Drive scopes
- **Microsoft**: Graph API tokens with Mail, Calendar, Files permissions

## Setup and Usage

### Step 1: Start Office Service in Demo Mode

```bash
# Navigate to office service directory
cd services/office

# Set demo environment variables
export DEMO_MODE=true
export DEMO_GOOGLE_TOKEN="your-google-oauth-token"
export DEMO_MICROSOFT_TOKEN="your-microsoft-graph-token"

# Optional: Set other service configuration
export DB_URL_USER="sqlite:///./office_service.db"
export REDIS_URL="redis://localhost:6379"

# Start the Office Service (from office service directory)
cd services/office
./start.sh
```

### Step 2: Run the Full Demo

```bash
# From repository root with unified environment
source venv/bin/activate
python services/demos/office_full.py user@example.com
```

## Demo Flow

The full demo performs these operations via HTTP API calls:

1. **🏥 Health Check**: Verifies Office Service is running and healthy
2. **🔌 Provider Integration Health**: Tests token availability for each provider
3. **📧 Email Operations**: 
   - Fetch unified email messages from all providers
   - Retrieve specific email by ID
4. **📅 Calendar Operations**:
   - Fetch upcoming calendar events
   - Display events from all connected providers
5. **📁 File Operations**:
   - List files from Google Drive and OneDrive
   - Perform cross-provider file search
6. **🎯 Summary**: Show success/failure status and demonstrate unified API benefits

## Sample Output

```
🚀 Office Service Full Integration Demo
============================================================
👤 User: user@example.com
🌐 Service URL: http://localhost:8003

==================================================
 🏥 HEALTH CHECK
==================================================
✅ Office Service is healthy
   Status: healthy
   Database: healthy
   Redis: healthy

==================================================
 🔌 PROVIDER INTEGRATION HEALTH
==================================================
✅ Provider integrations checked for user@example.com
   ✅ Google: healthy
   ✅ Microsoft: healthy

==================================================
 📧 EMAIL OPERATIONS
==================================================
📥 Fetching emails...
   Google: 5 messages
     1. From: sender@gmail.com | Subject: Important Meeting Tomorrow
     2. From: boss@company.com | Subject: Weekly Status Update
   Microsoft: 3 messages
     1. From: colleague@work.com | Subject: Project Proposal Review
✅ Total emails fetched: 8
📄 Fetching specific email: gmail_abc123
   ✅ Retrieved: Important Meeting Tomorrow

==================================================
 🎯 DEMO SUMMARY
==================================================
✅ All operations completed successfully!
🎉 The Office Service unified API is working perfectly!

🔥 This demonstrates the power of the unified Office Service API:
   • Single HTTP endpoint for multiple providers
   • Standardized response formats
   • Automatic token management
   • Error handling and logging
   • Caching and rate limiting
```

## Demo Mode Features

### Token Management Override

The `DemoTokenManager` bypasses the user management service by:
- Reading tokens from `DEMO_GOOGLE_TOKEN` and `DEMO_MICROSOFT_TOKEN` environment variables
- Returning the same tokens for any user ID (perfect for demos)
- Eliminating the need for a separate user management service

### Configuration

Set `DEMO_MODE=true` in the Office Service environment to enable:
- Demo token manager instead of HTTP calls to user service
- Simplified token lookup using environment variables
- Consistent demo experience across different environments

## Troubleshooting

### "Connection refused" errors
- Make sure the Office Service is running on the specified port
- Check that `DEMO_MODE=true` is set in the Office Service environment
- Verify the service started without errors

### "No token available" errors
- Ensure `DEMO_GOOGLE_TOKEN` and/or `DEMO_MICROSOFT_TOKEN` are set in the Office Service environment
- Verify your tokens are valid and have the required scopes
- Check the Office Service logs for token retrieval errors

### Import errors
- Make sure you're running from the repository root directory
- Ensure all dependencies are installed: `pip install -r services/office/requirements.txt`

## Production Considerations

This demo mode is perfect for:
- **Development**: Test the Office Service without complex user management setup
- **Demos**: Showcase the unified API capabilities 
- **CI/CD**: Automated testing with known token values
- **Documentation**: Generate examples and screenshots

For production use:
- Implement proper user management service
- Use real OAuth flows with refresh tokens
- Enable proper rate limiting and monitoring
- Set up database migrations and monitoring 