# Full Briefly Demo

This comprehensive demo integrates all three Briefly services (chat, office, user) to provide a complete experience with OAuth authentication and enhanced functionality.

## Features

- **Unified Chat Interface**: Seamless integration of all services
- **OAuth Authentication**: Automatic setup with Google and Microsoft integrations
- **Draft Management**: Create, delete, and send drafts via email
- **Service Health Monitoring**: Real-time service availability checking
- **Graceful Fallbacks**: Continues working even if some services are unavailable
- **Dual Modes**: API mode (default) and local multi-agent mode

## Prerequisites

1. **Services Running**:
   - Chat Service: `http://localhost:8002`
   - User Service: `http://localhost:8001`
   - Office Service: `http://localhost:8003`

2. **Optional OAuth Setup**:
   - Google OAuth credentials (for Google integrations)
   - Microsoft OAuth credentials (for Microsoft integrations)
   - OAuth callback handler utilities

## Quick Start

### 1. Default API Mode
```bash
python services/demos/full_demo.py
```

This will:
- Check all service availability
- Set up authentication if user service is available
- Present the enhanced chat interface
- Support draft management commands

### 2. Local Multi-Agent Mode
```bash
python services/demos/full_demo.py --local
```

This runs the chat system locally without requiring the chat service API.

### 3. Skip Authentication
```bash
python services/demos/full_demo.py --no-auth
```

This skips the OAuth setup process.

## Enhanced Commands

### Chat Commands
- Type any message to chat with Briefly
- `help` - Show all available commands
- `exit` or `quit` - Exit the demo

### Draft Management
- `delete` - Delete the current draft
- `send` - Send current draft via email

### Thread Management (API Mode)
- `list` - List all chat threads
- `new` - Start a new thread
- `switch <thread_id>` - Switch to existing thread

### System Commands
- `status` - Show service and integration status
- `auth` - Re-authenticate with services
- `clear` - Clear conversation history (local mode only)

## Advanced Usage

### Custom Service URLs
```bash
python services/demos/full_demo.py \
  --chat-url http://localhost:8002 \
  --user-url http://localhost:8001 \
  --office-url http://localhost:8003
```

### Single Message Mode
```bash
python services/demos/full_demo.py --message "Draft an email about the meeting"
```

## OAuth Integration

If the user service is available and OAuth utilities are installed, the demo will:

1. Automatically create authentication tokens
2. Check for existing integrations
3. Offer to set up Google and Microsoft OAuth
4. Open browser windows for authentication
5. Handle OAuth callbacks automatically

## Service Dependencies

The demo gracefully handles partial service availability:

- **Chat Service Only**: Basic chat functionality
- **Chat + User Service**: Chat with authentication
- **Chat + Office Service**: Chat with email sending
- **All Services**: Full functionality including OAuth

## Error Handling

The demo includes comprehensive error handling:
- Service unavailability warnings
- OAuth flow failures
- Network timeout handling
- Graceful degradation of features

## Configuration

### Environment Variables
- `API_FRONTEND_USER_KEY` - API key for user service
- `LITELLM_LOG` - Set to "WARNING" to reduce logging noise

### Service URLs
All service URLs can be customized via command line arguments:
- `--chat-url` - Chat service URL
- `--user-url` - User service URL  
- `--office-url` - Office service URL

## Troubleshooting

### Service Connection Issues
1. Verify services are running on expected ports
2. Check firewall and network connectivity
3. Review service logs for errors

### OAuth Issues
1. Ensure OAuth credentials are properly configured
2. Check redirect URI configuration
3. Verify callback handler is accessible

### Authentication Errors
1. Check API key configuration
2. Verify JWT token generation
3. Review user service authentication logs

## Examples

### Basic Chat Session
```
🚀 Welcome to the Full Briefly Demo!
💬 demo_user: Draft an email about tomorrow's meeting
🤖 Briefly: I've drafted an email about tomorrow's meeting...
💬 demo_user: send
📧 ✅ Draft sent via email
```

### Thread Management
```
💬 demo_user: list
📋 Your threads:
  • 1234567890: Meeting discussion
  • 1234567891: Project updates
💬 demo_user: switch 1234567890
✅ Switched to thread 1234567890
```

### Service Status Check
```
💬 demo_user: status
📊 System Status:
  Chat Service: ✅
  Office Service: ✅
  User Service: ✅

🔗 Integrations:
  Google: ✅
  Microsoft: ❌
```

## Integration with Existing Demos

This demo complements the existing service-specific demos:
- Uses patterns from `chat.py`
- Incorporates OAuth flows from `user_management_demo.py`
- Integrates email functionality from `office_full.py`

## Development

To extend the demo:
1. Add new service clients to the `FullDemo` class
2. Implement new command handlers
3. Update help text and documentation
4. Add error handling for new functionality 