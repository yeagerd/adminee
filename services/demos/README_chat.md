# Chat Service Demo

A comprehensive demo client for testing the Briefly Chat Service with NextAuth integration and multi-agent workflow capabilities.

## Features

- **Email-to-User-ID Resolution**: Automatically resolves email addresses to user IDs using email normalization
- **NextAuth Integration**: Testing environment for NextAuth authentication flows
- **OAuth Integration**: Support for Google and Microsoft OAuth flows
- **Multi-Agent Workflows**: Test complex AI agent interactions
- **Service Health Monitoring**: Real-time status of all Briefly services
- **User Preference Management**: Timezone and UI preference handling

## Prerequisites

1. **Services Running**: Ensure the following services are running:
   - User Service (port 8001)
   - Chat Service (port 8002) 
   - Office Service (port 8003) - optional for OAuth features

2. **Dependencies**: Install required packages:
   ```bash
   cd services/demos
   pip install httpx fastapi uvicorn python-jose[cryptography]
   ```

3. **Environment Variables**: Set up required environment variables:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export NEXTAUTH_SECRET="your-nextauth-secret"  # for JWT token creation
   ```

## Quick Start

### Basic Usage

```bash
# Start the demo with default settings
python chat.py

# Use a specific email for authentication
python chat.py --user john.doe@gmail.com

# Skip authentication (for testing)
python chat.py --no-auth

# Use local multi-agent mode instead of API
python chat.py --local
```

### Authentication Flow

The demo now uses **email-to-user-ID resolution** for a more robust authentication experience:

1. **Email Resolution**: The demo calls `GET /users?email=...` to convert email addresses to `external_auth_id`
2. **Email Normalization**: Handles provider-specific email formats automatically:
   - **Gmail**: Removes dots and plus addressing (`john.doe+work@gmail.com` → `johndoe@gmail.com`)
   - **Outlook**: Removes plus addressing (`jane.smith+news@outlook.com` → `jane.smith@outlook.com`) 
   - **Yahoo**: Removes dots and plus addressing (`bob.wilson+alerts@yahoo.com` → `bobwilson@yahoo.com`)
3. **User Creation**: If no user exists, automatically creates one with the resolved email
4. **JWT Token**: Generates a NextAuth-compatible JWT token for service authentication

### Email Resolution Examples

The authentication system now handles various email formats transparently:

```bash
# These all resolve to the same user (if they exist):
python chat.py --user john.doe@gmail.com
python chat.py --user j.o.h.n.d.o.e@gmail.com  
python chat.py --user john.doe+work@gmail.com
python chat.py --user johndoe@googlemail.com

# Outlook variations:
python chat.py --user jane.smith@outlook.com
python chat.py --user jane.smith+newsletters@outlook.com
```

## Available Commands

Once the demo is running, you can use these commands:

### Chat Commands
- `help` - Show available commands
- `status` - Check service health and authentication status
- `send` - Send current draft via email (requires OAuth integration)
- `delete` - Delete current draft
- `auth [email]` - Re-authenticate with optional different email
- `timezone <timezone>` - Set user timezone (e.g., `timezone America/New_York`)

### OAuth Commands  
- `oauth google` - Set up Google OAuth integration
- `oauth microsoft` - Set up Microsoft OAuth integration

### NextAuth Testing Commands
- `nextauth <provider>` - Test NextAuth flow with provider
- `compare` - Compare different authentication approaches
- `demo-nextauth` - Run comprehensive NextAuth integration demo

### API Commands (when using `--api` mode)
- `api threads` - List chat threads
- `api stream <message>` - Send message with streaming response

## Error Handling

The new authentication flow includes comprehensive error handling:

### Email Resolution Errors
- **404 Not Found**: User doesn't exist, will attempt to create new user
- **422 Validation Error**: Invalid email format 
- **500 Server Error**: User service temporarily unavailable
- **Timeout**: Request timeout, service may be slow
- **Network Error**: Connectivity issues

### User Creation Errors  
- **409 Conflict**: Email collision detected during user creation
- **422 Validation**: Invalid user data provided
- **500 Server Error**: Database or service issues

### Authentication Errors
- **Token Creation**: NextAuth JWT token generation failures
- **Service Verification**: Token validation against user service

## Configuration

### Service URLs
Default service URLs can be modified:
```bash
python chat.py --chat-url http://localhost:8002 --user-url http://localhost:8001 --office-url http://localhost:8003
```

### Timeout Settings
The demo uses a 30-second timeout for all HTTP requests. This can handle slower service responses during development.

## Troubleshooting

### Common Issues

1. **"User service not available"**
   - Ensure user service is running on port 8001
   - Check service health: `curl http://localhost:8001/health`

2. **"Email resolution failed"**
   - Verify email format is valid
   - Check user service logs for detailed error messages
   - Try with a different email address

3. **"Authentication failed"**
   - Ensure NEXTAUTH_SECRET environment variable is set
   - Check that the user service accepts the JWT tokens
   - Verify the auth provider configuration

4. **"OAuth flow failed"**
   - Ensure office service is running for OAuth integrations
   - Check that OAuth credentials are properly configured
   - Verify redirect URI configuration

5. **"Network timeout"**
   - Services may be slow to start up
   - Check Docker container status if using containers
   - Increase timeout settings if needed

### Debug Mode

Enable detailed logging:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../.."
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('chat.py').read())
"
```

### Service Health Check

Manually verify service connectivity:
```bash
# Check user service
curl http://localhost:8001/health

# Check chat service  
curl http://localhost:8002/health

# Check office service
curl http://localhost:8003/health

# Test email resolution directly
curl -X GET "http://localhost:8001/users?email=test@gmail.com"
```

## Example API Calls

### Email Resolution
```bash
# Resolve email to user ID
curl -X GET "http://localhost:8001/users?email=john.doe+work@gmail.com"

# Response:
{
  "external_auth_id": "user_abc123",
  "email": "john.doe@gmail.com", 
  "normalized_email": "johndoe@gmail.com",
  "auth_provider": "clerk"
}
```

### User Creation
```bash
# Create new user
curl -X POST http://localhost:8001/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "external_auth_id": "user_demo123",
    "auth_provider": "nextauth", 
    "email": "demo@example.com",
    "first_name": "Demo",
    "last_name": "User"
  }'
```

## Integration with Other Services

This demo demonstrates integration patterns for:

- **User Management**: Authentication, preferences, timezone handling
- **Chat Service**: Multi-agent workflows, conversation management
- **Office Service**: Email sending, calendar integration via OAuth
- **Frontend**: JWT token patterns, error handling, user experience flows

The email resolution system provides a foundation for robust user identification across all Briefly services.
