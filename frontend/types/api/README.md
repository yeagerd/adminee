# Auto-Generated API Types

This directory contains TypeScript types automatically generated from OpenAPI schemas.

## Structure

- `chat/` - Types for the Chat service
- `meetings/` - Types for the Meetings service  
- `office/` - Types for the Office service (Google/Microsoft integrations)
- `user/` - Types for the User Management service
- `shipments/` - Types for the Shipments service
- `email-sync/` - Types for the Email Sync service
- `vector-db/` - Types for the Vector Database service

## Generation

Types are generated using the `openapi-typescript-codegen` tool from OpenAPI schemas.

### Regenerate Types

```bash
# From the frontend directory
npm run generate-types

# Or use the script directly
./scripts/generate-types.sh  # Unix
./scripts/generate-types.bat # Windows
```

### Individual Service Types

```bash
npm run generate-types:chat
npm run generate-types:meetings
npm run generate-types:office
npm run generate-types:user
npm run generate-types:shipments
npm run generate-types:email-sync
npm run generate-types:vector-db
```

## Usage

```typescript
import { ChatRequest, ChatResponse } from '@/types/api/chat';
import { UserResponse } from '@/types/api/user';
import { Package } from '@/types/api/shipments';

// Use the generated types in your components
const handleChat = async (request: ChatRequest): Promise<ChatResponse> => {
  // Implementation
};
```

## Notes

- **DO NOT** manually edit these files - they will be overwritten
- Types are generated from the backend Pydantic models
- This ensures single source of truth between frontend and backend
- Run `npm run typecheck` after generation to verify types are valid
