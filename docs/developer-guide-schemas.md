# Developer Guide: Working with Improved Schemas

## Introduction

This guide explains how to work with the improved schemas and generated types in the Briefly project. The schemas now provide better type safety, clearer API contracts, and improved developer experience.

## Schema Architecture

### 1. Backend Schemas (Pydantic Models)

All API schemas are defined using Pydantic models in the respective service directories:

```
services/
├── office/
│   └── schemas/
│       └── __init__.py  # Contains all Pydantic models
├── user/
│   └── schemas/
│       └── __init__.py
├── shipments/
│   └── schemas/
│       └── __init__.py
└── ...
```

### 2. Generated Types (TypeScript)

TypeScript types are automatically generated from the OpenAPI schemas:

```
frontend/
└── types/
    └── api/
        ├── office/
        │   └── models/
        │       ├── Contact.ts
        │       ├── ContactList.ts
        │       ├── ContactCreateResponse.ts
        │       └── ...
        ├── user/
        │   └── models/
        │       ├── IntegrationProvider.ts
        │       ├── IntegrationResponse.ts
        │       └── ...
        └── shipments/
            └── models/
                ├── PackageOut.ts
                ├── PackageCreate.ts
                └── ...
```

## Working with Backend Schemas

### 1. Creating New Response Models

When creating new API endpoints, define specific response models:

```python
from pydantic import BaseModel
from typing import Optional, List

class UserResponse(BaseModel):
    """Response model for user operations."""
    
    success: bool
    user: Optional[User] = None
    error: Optional[Dict[str, Any]] = None
    request_id: str

class UserListResponse(BaseModel):
    """Response model for user list operations."""
    
    success: bool
    users: Optional[List[User]] = None
    total_count: int
    error: Optional[Dict[str, Any]] = None
    request_id: str
```

### 2. Using Response Models in Endpoints

Always use the `response_model` parameter in FastAPI endpoints:

```python
@router.get("/users", response_model=UserListResponse)
async def get_users() -> UserListResponse:
    try:
        users = await user_service.get_all_users()
        return UserListResponse(
            success=True,
            users=users,
            total_count=len(users),
            request_id=get_request_id()
        )
    except Exception as e:
        return UserListResponse(
            success=False,
            error={"message": str(e)},
            total_count=0,
            request_id=get_request_id()
        )
```

### 3. Avoiding Generic Types

❌ **Don't do this:**
```python
@router.get("/users", response_model=Dict[str, Any])
async def get_users() -> Dict[str, Any]:
    return {"users": users, "count": len(users)}
```

✅ **Do this instead:**
```python
@router.get("/users", response_model=UserListResponse)
async def get_users() -> UserListResponse:
    return UserListResponse(
        success=True,
        users=users,
        total_count=len(users),
        request_id=get_request_id()
    )
```

## Working with Generated Types

### 1. Importing Types

Import types from the generated API modules:

```typescript
// ✅ Correct - import from generated types
import type { Contact, ContactList } from '@/types/api/office';
import type { IntegrationProvider } from '@/types/api/user';
import type { PackageOut } from '@/types/api/shipments';

// ❌ Don't import from @/types (legacy)
import type { Contact } from '@/types';
```

### 2. Using Generated Types

The generated types provide full type safety:

```typescript
interface ContactListProps {
  contacts: Contact[];  // Generated type with full structure
  onSelect: (contact: Contact) => void;
}

function ContactList({ contacts, onSelect }: ContactListProps) {
  return (
    <div>
      {contacts.map(contact => (
        <div key={contact.id}>
          <h3>{contact.full_name || 'Unknown'}</h3>
          <p>{contact.primary_email?.email}</p>
          <button onClick={() => onSelect(contact)}>
            Select
          </button>
        </div>
      ))}
    </div>
  );
}
```

### 3. Handling Null vs Undefined

The generated types use `(string | null)` for optional fields:

```typescript
// Generated type
interface Contact {
  full_name: (string | null);
  primary_email: (EmailAddress | null);
}

// Safe handling
function ContactDisplay({ contact }: { contact: Contact }) {
  const displayName = contact.full_name || 'Unknown';
  const email = contact.primary_email?.email || 'No email';
  
  return (
    <div>
      <h3>{displayName}</h3>
      <p>{email}</p>
    </div>
  );
}
```

### 4. Working with Enums

Generated enums provide type-safe constants:

```typescript
import { IntegrationProvider } from '@/types/api/user';

// ✅ Type-safe usage
const provider = IntegrationProvider.GOOGLE;

// ❌ Won't compile - invalid value
const provider = 'invalid_provider';

// Safe comparison
if (provider === IntegrationProvider.MICROSOFT) {
  // Handle Microsoft-specific logic
}
```

## API Client Usage

### 1. Using Generated API Clients

The generated types work seamlessly with API clients:

```typescript
import { officeApi } from '@/api';
import type { ContactList } from '@/types/api/office';

async function fetchContacts(): Promise<ContactList> {
  const response = await officeApi.getContacts(['google'], 100);
  
  // response is fully typed as ContactList
  if (response.success && response.data) {
    return response.data;  // Type: Contact[]
  }
  
  throw new Error('Failed to fetch contacts');
}
```

### 2. Type-Safe API Responses

All API responses are now properly typed:

```typescript
// Before - generic response
const response: any = await api.getContacts();
const contacts = response.data?.contacts || [];

// After - typed response
const response: ContactList = await api.getContacts();
const contacts = response.data || [];  // Type: Contact[]
```

## Best Practices

### 1. Always Use Generated Types

```typescript
// ✅ Use generated types
import type { Contact } from '@/types/api/office';

// ❌ Don't create custom interfaces
interface Contact {
  id: string;
  name: string;
  // Missing fields, may be outdated
}
```

### 2. Handle Optional Fields Safely

```typescript
// ✅ Safe handling with fallbacks
const name = contact.full_name || 'Unknown';
const email = contact.primary_email?.email || 'No email';

// ❌ Unsafe access
const name = contact.full_name;  // Could be null
const email = contact.primary_email.email;  // Could throw error
```

### 3. Use Type Guards for Complex Logic

```typescript
function isValidContact(contact: Contact): boolean {
  return !!(
    contact.id &&
    contact.full_name &&
    contact.primary_email?.email
  );
}

// Usage
const validContacts = contacts.filter(isValidContact);
```

### 4. Leverage TypeScript's Type System

```typescript
// Type-safe event handlers
function handleContactSelect(contact: Contact) {
  // TypeScript knows contact has all required fields
  console.log(`Selected: ${contact.full_name} (${contact.id})`);
}

// Type-safe API calls
async function updateContact(id: string, updates: Partial<Contact>) {
  // TypeScript ensures updates only contains valid Contact fields
  const response = await api.updateContact(id, updates);
  return response;
}
```

## Troubleshooting

### 1. Type Mismatches

If you encounter type mismatches:

```typescript
// Check the generated type
import type { Contact } from '@/types/api/office';

// Verify the structure matches
const contact: Contact = {
  id: '123',
  full_name: 'John Doe',
  // ... other required fields
};
```

### 2. Null vs Undefined Issues

```typescript
// Generated types use (string | null)
const name: string | null = contact.full_name;

// Handle both cases
const displayName = name ?? 'Unknown';  // nullish coalescing
// or
const displayName = name || 'Unknown';  // logical OR
```

### 3. Missing Properties

If a property seems to be missing:

1. Check the generated type definition
2. Verify the backend schema includes the field
3. Regenerate types: `npm run generate-types`

### 4. Schema Generation Issues

If schemas aren't generating correctly:

1. Check for syntax errors in Pydantic models
2. Verify FastAPI app imports are correct
3. Run schema generation manually: `./scripts/generate-openapi-schemas.sh office`

## Development Workflow

### 1. Adding New Endpoints

1. Define Pydantic response models in `schemas/__init__.py`
2. Use `response_model` in FastAPI endpoints
3. Return properly typed responses
4. Regenerate schemas: `./scripts/generate-openapi-schemas.sh office`
5. Regenerate types: `npm run generate-types`
6. Use generated types in frontend components

### 2. Modifying Existing Schemas

1. Update Pydantic models in backend
2. Regenerate schemas and types
3. Update frontend components to use new types
4. Test for type compatibility issues

### 3. Testing Schema Changes

1. Run backend tests: `pytest services/office/tests/`
2. Check schema generation: `./scripts/generate-openapi-schemas.sh office`
3. Validate TypeScript types: `npm run validate-types`
4. Test frontend components with new types

## Conclusion

The improved schemas provide a solid foundation for type-safe development. By following these guidelines, you can:

- Write more reliable code
- Catch errors at compile time
- Have better IDE support
- Maintain consistent API contracts
- Improve overall code quality

Remember: Always use generated types, handle optional fields safely, and leverage TypeScript's type system for better development experience.
