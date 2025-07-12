# Briefly Express API Gateway

A production-ready Express.js API gateway that provides authentication, security, and proxying for the Briefly platform.

## Features

### 🔐 Authentication & Security
- **NextAuth JWT Validation**: Validates tokens from your NextAuth.js frontend
- **Malicious Traffic Filtering**: Blocks suspicious user agents, headers, and parameters
- **Rate Limiting**: Tiered rate limiting (strict for chat, standard for other endpoints)
- **Security Headers**: Helmet.js with CSP, XSS protection, and more
- **CORS Protection**: Configurable CORS with credentials support

### 🌐 Proxy Capabilities
- **WebSocket Support**: Full WebSocket proxying for real-time features
- **Server-Sent Events (SSE)**: Streaming support for chat responses
- **User Identity Forwarding**: Passes user context to backend services
- **Request Tracing**: Adds request IDs for debugging

### 🛡️ Security Features
- **Bot Detection**: Blocks common bot user agents
- **Payload Size Limits**: Prevents large payload attacks
- **Suspicious Header Detection**: Blocks requests with forged headers
- **Parameter Injection Protection**: Blocks common attack patterns
- **Token Validation**: Comprehensive JWT validation with expiration checks

## Quick Start

### 1. Install Dependencies
```bash
cd frontend/components/gateway
npm install
```

### 2. Environment Variables
Create a `.env` file in the gateway directory:
```bash
# Gateway Configuration
PORT=3001
NODE_ENV=development

# NextAuth Configuration
NEXTAUTH_SECRET=your-nextauth-secret-here

# Service URLs
USER_SERVICE_URL=http://localhost:8001
CHAT_SERVICE_URL=http://localhost:8002
OFFICE_SERVICE_URL=http://localhost:8003
FRONTEND_URL=http://localhost:3000
```

### 3. Start the Gateway
```bash
# Development mode with auto-restart
npm run dev

# Production mode
npm start
```

## Architecture

```
Frontend (NextAuth) → Express Gateway → Backend Services
     ↓                      ↓              ↓
   JWT Token         Auth Validation    User Context
   Session           Rate Limiting      API Key Auth
   OAuth Flow        Security Filter    Business Logic
```

## API Endpoints

### Public Endpoints
- `GET /health` - Health check (no auth required)

### Protected Endpoints
- `/api/users/*` - User management service (port 8001)
  - User profiles, preferences, OAuth integrations
  - Endpoints: `/users`, `/users/{user_id}/preferences`, `/users/{user_id}/integrations`
- `/api/chat/*` - Chat service (port 8002, strict rate limiting)
  - Multi-agent workflow chat functionality
  - Endpoints: `/chat`, `/chat/stream`, `/threads`, `/threads/{thread_id}/history`
- `/api/calendar/*` - Office service (port 8003)
  - Google Calendar and Microsoft Calendar integration
  - Endpoints: `/calendar/events`, `/calendar/events/{event_id}`
- `/api/email/*` - Office service (port 8003)
  - Gmail and Microsoft Outlook integration
  - Endpoints: `/email/messages`, `/email/messages/{message_id}`, `/email/send`
- `/api/files/*` - Office service (port 8003)
  - Google Drive and Microsoft OneDrive integration
  - Endpoints: `/files`, `/files/search`, `/files/{file_id}`

- `/api/*` (fallback) - User management service (port 8001)

## Security Configuration

### Rate Limiting
- **Chat Endpoints** (`/api/chat/*`): 30 requests/minute per user
- **Other Endpoints**: 100 requests/minute per user
- **Key Generation**: Uses user ID when available, falls back to IP

### Malicious Traffic Filtering
- **User Agent Blocking**: Blocks bots, crawlers, and suspicious tools
- **Header Validation**: Blocks forged forwarding headers
- **Parameter Sanitization**: Blocks injection attempts
- **Payload Size Limits**: Prevents large payload attacks

### JWT Validation
- **Token Verification**: Validates signature and claims
- **Expiration Check**: Ensures tokens haven't expired
- **Future Token Check**: Prevents clock skew attacks
- **Required Claims**: Validates subject claim

## WebSocket Support

The gateway fully supports WebSocket connections:

```javascript
// Frontend WebSocket connection
const ws = new WebSocket('ws://localhost:3001/api/chat/ws');

// The gateway will:
// 1. Validate the JWT token in the connection request
// 2. Forward user context to the backend
// 3. Proxy the WebSocket connection
```

## Server-Sent Events (SSE)

For streaming responses:

```javascript
// Frontend SSE connection
const eventSource = new EventSource('http://localhost:3001/api/chat/stream');

// The gateway will:
// 1. Validate the JWT token
// 2. Disable response buffering
// 3. Stream the response in real-time
```

## Monitoring & Logging

The gateway provides comprehensive logging:

- **Authentication Events**: Successful/failed logins
- **Security Events**: Blocked requests and attacks
- **Proxy Events**: Request forwarding and responses
- **Error Events**: Detailed error information

## Production Deployment

### Docker Deployment
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3001
CMD ["npm", "start"]
```

### Environment Variables for Production
```bash
NODE_ENV=production
PORT=3001
NEXTAUTH_SECRET=your-production-secret
BACKEND_URL=https://your-backend.com
FRONTEND_URL=https://your-frontend.com
```

### Load Balancer Configuration
- **Health Check**: `GET /health`
- **Sticky Sessions**: Enable for WebSocket support
- **SSL Termination**: Handle at load balancer level

## Troubleshooting

### Common Issues

**JWT Validation Errors**
```
Error: Invalid or expired token
```
- Check `NEXTAUTH_SECRET` matches frontend
- Verify token expiration times
- Check clock synchronization

**WebSocket Connection Issues**
```
Error: WebSocket upgrade failed
```
- Ensure gateway is running on correct port
- Check CORS configuration
- Verify JWT token in connection request

**Rate Limiting Issues**
```
Error: Too many requests from this IP
```
- Check rate limit configuration
- Verify user authentication
- Monitor for potential abuse

### Debug Mode
Set `NODE_ENV=development` for detailed logging:
```bash
NODE_ENV=development npm run dev
```

## Future Enhancements

### Planned Features
- **Metrics Collection**: Prometheus/Grafana integration
- **Circuit Breaker**: Automatic service failure handling
- **Request Caching**: Redis-based response caching
- **API Versioning**: Support for multiple API versions
- **Advanced Analytics**: Request patterns and usage metrics

### Migration to Managed Services
When scaling, consider migrating to:
- **Google Cloud API Gateway** (GCP)
- **AWS API Gateway** (AWS)
- **Azure API Management** (Azure)

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Test with WebSocket and SSE endpoints

## License

MIT License - see LICENSE file for details 