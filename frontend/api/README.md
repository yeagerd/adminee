# Frontend API Client Library

This directory contains the refactored API client library for communicating with the Briefly backend services via the gateway.

## Structure

```
api/
├── clients/           # Service-specific API clients
│   ├── gateway-client.ts      # Base HTTP client with authentication
│   ├── office-client.ts       # Email, calendar, and contacts APIs
│   ├── chat-client.ts         # Chat completions and draft management
│   ├── user-client.ts         # User management and integrations
│   ├── meetings-client.ts     # Meeting poll management
│   └── shipments-client.ts    # Package tracking and shipment management
├── types/             # Common type definitions
│   └── common.ts      # Shared interfaces and types
├── index.ts           # Barrel exports and convenience instances
└── README.md          # This file
```

## Architecture

### Base Client
- **`GatewayClient`**: Abstract base class providing core HTTP functionality
  - Authentication via NextAuth session tokens
  - Error handling and response parsing
  - Environment validation
  - WebSocket support
  - Date normalization utilities

### Service Clients
Each service client extends `GatewayClient` and provides domain-specific methods:

- **`OfficeClient`**: Email, calendar, and contacts management
- **`ChatClient`**: Chat completions, threads, and draft management
- **`UserClient`**: User preferences and integration management
- **`MeetingsClient`**: Meeting poll creation and management
- **`ShipmentsClient`**: Package tracking and shipment data

## Usage

### Import and Use

```typescript
// Import specific clients
import { OfficeClient, ChatClient } from '@/api';

// Create instances
const officeApi = new OfficeClient();
const chatApi = new ChatClient();

// Use the APIs
const emails = await officeApi.getEmails(['google'], 50);
const response = await chatApi.chat('Hello, how can you help me?');
```

### Convenience Instances

Pre-configured instances are available for common use cases:

```typescript
import { officeApi, chatApi, userApi, meetingsApi, shipmentsApi } from '@/api';

// Use directly
const user = await userApi.getCurrentUser();
const packages = await shipmentsApi.getPackages();
```

### Type Safety

All clients provide full TypeScript support with proper interfaces:

```typescript
import { MeetingPoll, PackageResponse } from '@/api';

// Type-safe API calls
const poll: MeetingPoll = await meetingsApi.getMeetingPoll('poll-123');
const package: PackageResponse = await shipmentsApi.getPackage('pkg-456');
```

## Migration from Old Structure

### Before (Monolithic)
```typescript
import { gatewayClient } from '@/lib/gateway-client';

// All APIs mixed together
await gatewayClient.getCalendarEvents();
await gatewayClient.createEmailDraft();
await gatewayClient.parseEmail();
```

### After (Service-Specific)
```typescript
import { officeApi, shipmentsApi } from '@/api';

// Clear separation of concerns
await officeApi.getCalendarEvents();
await officeApi.createEmailDraft();
await shipmentsApi.parseEmail();
```

## Benefits

1. **Clear Separation**: Each service has its own client with focused responsibilities
2. **Better Type Safety**: Service-specific types and interfaces
3. **Easier Testing**: Mock individual services instead of the entire gateway
4. **Improved Maintainability**: Changes to one service don't affect others
5. **Better Developer Experience**: IntelliSense shows only relevant methods
6. **Consistent Patterns**: All clients follow the same architecture

## Adding New Services

To add a new service:

1. Create a new client class extending `GatewayClient`
2. Add service-specific types and interfaces
3. Export the client from `api/index.ts`
4. Create a convenience instance

Example:
```typescript
// api/clients/new-service-client.ts
export class NewServiceClient extends GatewayClient {
  async getData(): Promise<DataResponse> {
    return this.request('/api/v1/new-service/data');
  }
}

// api/index.ts
export { NewServiceClient } from './clients/new-service-client';
export const newServiceApi = new NewServiceClient();
```

## Error Handling

All clients inherit error handling from `GatewayClient`:

- HTTP errors are converted to descriptive Error objects
- Network errors are logged (except in test environments)
- Response parsing handles both JSON and text responses
- Authentication errors are handled gracefully

## Testing

Each service can be tested independently:

```typescript
import { OfficeClient } from '@/api/clients/office-client';

// Mock the base client for testing
jest.mock('@/api/clients/gateway-client');
const mockOfficeApi = new OfficeClient();
```

## Environment Variables

Required environment variables:
- `NEXT_PUBLIC_GATEWAY_URL`: Gateway service URL

The client validates these on instantiation and provides helpful error messages.
