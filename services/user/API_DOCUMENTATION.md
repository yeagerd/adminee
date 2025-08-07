# Briefly User Service API Documentation

## Overview

The Briefly User Service provides user management, authentication, and profile functionality. This service uses **cursor-based pagination** for all list endpoints to ensure consistent results and better performance.

## Cursor-Based Pagination

### Why Cursor-Based Pagination?

- **Performance**: Faster queries for large datasets
- **Consistency**: More reliable results with concurrent updates
- **Scalability**: Better handling of frequently updated data
- **Security**: Tamper-proof pagination tokens

### How It Works

Instead of using page numbers and offsets, cursor-based pagination uses a "cursor" token that points to a specific item in the dataset. This cursor is a signed, URL-safe token that contains:

- `last_id`: ID of the last user in the current page
- `last_created_at`: Timestamp for consistent ordering
- `filters`: Active filter parameters (query, email, onboarding_completed)
- `direction`: Navigation direction ('next' or 'prev')
- `limit`: Number of items per page

### Pagination Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cursor` | string | No | Cursor token for pagination (obtained from previous response) |
| `limit` | integer | No | Number of items per page (1-100, default: 20) |
| `direction` | string | No | Pagination direction: 'next' or 'prev' (default: 'next') |

### Pagination Response

```json
{
  "users": [...],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoxMjMsImxhc3RfY3JlYXRlZF9hdCI6IjIwMjQtMDMtMTNUMTA6MzA6MDAiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=",
    "prev_cursor": null,
    "has_next": true,
    "has_prev": false,
    "limit": 20
  }
}
```

### Usage Examples

#### First Page
```bash
GET /api/v1/users/search?limit=10
```

#### Next Page
```bash
GET /api/v1/users/search?cursor=eyJsYXN0X2lkIjoxMjMsImxhc3RfY3JlYXRlZF9hdCI6IjIwMjQtMDMtMTNUMTA6MzA6MDAiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoxMH0=&limit=10
```

#### Previous Page
```bash
GET /api/v1/users/search?cursor=eyJsYXN0X2lkIjoxMjMsImxhc3RfY3JlYXRlZF9hdCI6IjIwMjQtMDMtMTNUMTA6MzA6MDAiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoicHJldiIsImxpbWl0IjoxMH0=&direction=prev&limit=10
```

#### With Filters
```bash
GET /api/v1/users/search?query=john&email=john@example.com&onboarding_completed=true&limit=15
```

## API Endpoints

### User Search

#### GET /api/v1/users/search

Search users with cursor-based pagination. This endpoint is primarily for administrative or service use.

**Query Parameters:**
- `cursor` (optional): Cursor token for pagination
- `limit` (optional): Number of users per page (1-100, default: 20)
- `direction` (optional): Pagination direction ('next' or 'prev', default: 'next')
- `query` (optional): Search query for name or email (max 255 characters)
- `email` (optional): Filter by exact email address
- `onboarding_completed` (optional): Filter by onboarding status (true/false)

**Response:**
```json
{
  "users": [
    {
      "id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
      "email": "john.doe@example.com",
      "name": "John Doe",
      "onboarding_completed": true,
      "created_at": "2024-03-13T10:30:00Z",
      "updated_at": "2024-03-13T10:30:00Z",
      "preferences": {
        "timezone": "America/New_York",
        "language": "en",
        "notifications": {
          "email": true,
          "push": false
        }
      }
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoxMjQsImxhc3RfY3JlYXRlZF9hdCI6IjIwMjQtMDMtMTNUMTE6MDA6MDAiLCJmaWx0ZXJzIjp7InF1ZXJ5Ijoiam9obiIsImVtYWlsIjoiam9obkBleGFtcGxlLmNvbSIsIm9uYm9hcmRpbmdfY29tcGxldGVkIjp0cnVlfSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoxNX0=",
    "prev_cursor": null,
    "has_next": true,
    "has_prev": false,
    "limit": 15
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid cursor token or parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions (admin/service access required)
- `422 Unprocessable Entity`: Validation error in search parameters

### User Management

#### GET /api/v1/users/me

Get current user's profile information.

**Response:**
```json
{
  "id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
  "email": "john.doe@example.com",
  "name": "John Doe",
  "onboarding_completed": true,
  "created_at": "2024-03-13T10:30:00Z",
  "updated_at": "2024-03-13T10:30:00Z",
  "preferences": {
    "timezone": "America/New_York",
    "language": "en",
    "notifications": {
      "email": true,
      "push": false
    }
  }
}
```

#### PUT /api/v1/users/me

Update current user's profile information.

**Request Body:**
```json
{
  "name": "John Doe Updated",
  "preferences": {
    "timezone": "America/Los_Angeles",
    "language": "en",
    "notifications": {
      "email": true,
      "push": true
    }
  }
}
```

**Response:**
```json
{
  "id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
  "email": "john.doe@example.com",
  "name": "John Doe Updated",
  "onboarding_completed": true,
  "created_at": "2024-03-13T10:30:00Z",
  "updated_at": "2024-03-13T11:00:00Z",
  "preferences": {
    "timezone": "America/Los_Angeles",
    "language": "en",
    "notifications": {
      "email": true,
      "push": true
    }
  }
}
```

### Internal Endpoints

#### GET /api/v1/internal/users/{user_id}

Get user information by ID (internal service use only).

**Response:**
```json
{
  "id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
  "email": "john.doe@example.com",
  "name": "John Doe",
  "onboarding_completed": true,
  "created_at": "2024-03-13T10:30:00Z",
  "updated_at": "2024-03-13T10:30:00Z"
}
```

## Error Handling

### Cursor Validation Errors

When an invalid or expired cursor token is provided:

```json
{
  "detail": {
    "error": "Invalid or expired cursor token",
    "cursor_token": "invalid_token_here",
    "reason": "Token validation failed"
  }
}
```

### Common Error Codes

- `400 Bad Request`: Invalid parameters or cursor token
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error

## Authentication

### User-Facing Endpoints

- **Authentication**: JWT token or session-based authentication
- **User Context**: User ID extracted from authentication token
- **Access Control**: Users can only access their own data

### Internal/Service Endpoints

- **Authentication**: API key or service-to-service authentication
- **User Context**: User ID provided in path/query parameters
- **Access Control**: Service-level permissions required

## Migration Notes

**This is a breaking change.** The user service has migrated from offset-based pagination to cursor-based pagination. All API consumers must update their code to use the new pagination system.

### What Changed

- **Removed**: `page`, `page_size`, `total`, `has_next`, `has_previous` parameters and fields
- **Added**: `cursor`, `limit`, `direction` parameters
- **Updated**: All list endpoints now return cursor-based pagination metadata

### Migration Steps

1. Update API calls to use `cursor` instead of `page`
2. Use `limit` instead of `page_size`
3. Handle the new pagination response format
4. Update error handling for cursor validation errors

### Example Migration

**Before (Legacy):**
```javascript
// Request
GET /api/v1/users/search?page=2&page_size=20&query=john

// Response
{
  "users": [...],
  "total": 100,
  "page": 2,
  "page_size": 20,
  "has_next": true,
  "has_previous": true
}
```

**After (Cursor-Based):**
```javascript
// Request
GET /api/v1/users/search?cursor=eyJsYXN0X2lkIjoxMjMsImxhc3RfY3JlYXRlZF9hdCI6IjIwMjQtMDMtMTNUMTA6MzA6MDAiLCJmaWx0ZXJzIjp7InF1ZXJ5Ijoiam9obiJ9LCJkaXJlY3Rpb24iOiJuZXh0IiwibGltaXQiOjIwfQ==&limit=20&query=john

// Response
{
  "users": [...],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoxNDMsImxhc3RfY3JlYXRlZF9hdCI6IjIwMjQtMDMtMTNUMTE6MDA6MDAiLCJmaWx0ZXJzIjp7InF1ZXJ5Ijoiam9obiJ9LCJkaXJlY3Rpb24iOiJuZXh0IiwibGltaXQiOjIwfQ==",
    "prev_cursor": "eyJsYXN0X2lkIjoxMDMsImxhc3RfY3JlYXRlZF9hdCI6IjIwMjQtMDMtMTNUMTA6MDA6MDAiLCJmaWx0ZXJzIjp7InF1ZXJ5Ijoiam9obiJ9LCJkaXJlY3Rpb24iOiJwcmV2IiwibGltaXQiOjIwfQ==",
    "has_next": true,
    "has_prev": true,
    "limit": 20
  }
}
```

## Security

- Cursor tokens are signed and tamper-proof
- Tokens expire after 1 hour by default
- All tokens are URL-safe and can be used in query parameters
- Filter parameters are encoded within cursor tokens to maintain state
- User search endpoint requires admin/service permissions
- Input validation and sanitization on all parameters 