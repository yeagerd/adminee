# Briefly Shipments Service API Documentation

## Overview

The Briefly Shipments Service provides package shipment tracking, label management, and carrier integration. This service uses **cursor-based pagination** for all list endpoints to ensure consistent results and better performance.

## Cursor-Based Pagination

### Why Cursor-Based Pagination?

- **Performance**: Faster queries for large datasets
- **Consistency**: More reliable results with concurrent updates
- **Scalability**: Better handling of frequently updated data
- **Security**: Tamper-proof pagination tokens

### How It Works

Instead of using page numbers and offsets, cursor-based pagination uses a "cursor" token that points to a specific item in the dataset. This cursor is a signed, URL-safe token that contains:

- `last_id`: ID of the last item in the current page
- `last_updated`: Timestamp for consistent ordering
- `filters`: Active filter parameters
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
  "data": [...],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoiMTIzNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wIiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=",
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
GET /api/v1/shipments/packages?limit=10
```

#### Next Page
```bash
GET /api/v1/shipments/packages?cursor=eyJsYXN0X2lkIjoiMTIzNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wIiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoxMH0=&limit=10
```

#### Previous Page
```bash
GET /api/v1/shipments/packages?cursor=eyJsYXN0X2lkIjoiMTIzNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wIiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoicHJldiIsImxpbWl0IjoxMH0=&direction=prev&limit=10
```

#### With Filters
```bash
GET /api/v1/shipments/packages?carrier=fedex&status=in_transit&limit=15
```

## API Endpoints

### Packages

#### GET /api/v1/shipments/packages

List packages with cursor-based pagination.

**Query Parameters:**
- `cursor` (optional): Cursor token for pagination
- `limit` (optional): Number of packages per page (1-100, default: 20)
- `direction` (optional): Pagination direction ('next' or 'prev', default: 'next')
- `carrier` (optional): Filter by carrier (e.g., 'fedex', 'ups', 'usps')
- `status` (optional): Filter by status (e.g., 'in_transit', 'delivered', 'pending')
- `user_id` (optional): Filter by user ID

**Response:**
```json
{
  "data": [
    {
      "id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
      "tracking_number": "1Z999AA1234567890",
      "carrier": "ups",
      "status": "in_transit",
      "recipient_name": "John Doe",
      "recipient_address": "123 Main St, Anytown, USA",
      "estimated_delivery": "2024-03-15T10:00:00Z",
      "created_at": "2024-03-13T10:30:00Z",
      "updated_at": "2024-03-13T10:30:00Z",
      "events_count": 3
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoiMTIzNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wIiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7ImNhcnJpZXIiOiJmZWRleCIsInN0YXR1cyI6ImluX3RyYW5zaXQifSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoxNX0=",
    "prev_cursor": null,
    "has_next": true,
    "has_prev": false,
    "limit": 15
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid cursor token
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions

#### POST /api/v1/shipments/packages

Create a new package.

**Request Body:**
```json
{
  "tracking_number": "1Z999AA1234567890",
  "carrier": "ups",
  "recipient_name": "John Doe",
  "recipient_address": "123 Main St, Anytown, USA",
  "estimated_delivery": "2024-03-15T10:00:00Z"
}
```

**Response:**
```json
{
  "id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
  "tracking_number": "1Z999AA1234567890",
  "carrier": "ups",
  "status": "pending",
  "recipient_name": "John Doe",
  "recipient_address": "123 Main St, Anytown, USA",
  "estimated_delivery": "2024-03-15T10:00:00Z",
  "created_at": "2024-03-13T10:30:00Z",
  "updated_at": "2024-03-13T10:30:00Z",
  "events_count": 0
}
```

#### GET /api/v1/shipments/packages/{id}

Get a specific package by ID.

**Response:**
```json
{
  "id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
  "tracking_number": "1Z999AA1234567890",
  "carrier": "ups",
  "status": "in_transit",
  "recipient_name": "John Doe",
  "recipient_address": "123 Main St, Anytown, USA",
  "estimated_delivery": "2024-03-15T10:00:00Z",
  "created_at": "2024-03-13T10:30:00Z",
  "updated_at": "2024-03-13T10:30:00Z",
  "events_count": 3
}
```

### Events

#### GET /api/v1/shipments/events

List all events with cursor-based pagination.

**Query Parameters:**
- `cursor` (optional): Cursor token for pagination
- `limit` (optional): Number of events per page (1-100, default: 20)
- `direction` (optional): Pagination direction ('next' or 'prev', default: 'next')

**Response:**
```json
{
  "data": [
    {
      "id": "87654321-09fe-dcba-hgfe-lmnopqrstuvw",
      "package_id": "12345678-90ab-cdef-ghij-klmnopqrstuv",
      "event_type": "status_update",
      "description": "Package in transit",
      "location": "Memphis, TN",
      "timestamp": "2024-03-13T10:30:00Z",
      "created_at": "2024-03-13T10:30:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoiODc2NTQzMjEtMDlmZS1kY2JhLWhnZmUtbG1ub3BxcnN0dXZ3IiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=",
    "prev_cursor": null,
    "has_next": true,
    "has_prev": false,
    "limit": 20
  }
}
```

### Labels

#### GET /api/v1/shipments/labels

List all labels with cursor-based pagination.

**Query Parameters:**
- `cursor` (optional): Cursor token for pagination
- `limit` (optional): Number of labels per page (1-100, default: 20)
- `direction` (optional): Pagination direction ('next' or 'prev', default: 'next')

**Response:**
```json
{
  "data": [
    {
      "id": "11111111-2222-3333-4444-555555555555",
      "name": "urgent",
      "color": "#EF4444",
      "created_at": "2024-03-13T10:30:00Z"
    }
  ],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoiMTExMTExMTEtMjIyMi0zMzMzLTQ0NDQtNTU1NTU1NTU1NTU1IiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=",
    "prev_cursor": null,
    "has_next": true,
    "has_prev": false,
    "limit": 20
  }
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

## Migration Notes

**This is a breaking change.** The shipments service has migrated from offset-based pagination to cursor-based pagination. All API consumers must update their code to use the new pagination system.

### What Changed

- **Removed**: `page`, `per_page`, `total`, `total_pages` parameters and fields
- **Added**: `cursor`, `limit`, `direction` parameters
- **Updated**: All list endpoints now return cursor-based pagination metadata

### Migration Steps

1. Update API calls to use `cursor` instead of `page`
2. Use `limit` instead of `per_page`
3. Handle the new pagination response format
4. Update error handling for cursor validation errors

### Example Migration

**Before (Legacy):**
```javascript
// Request
GET /api/v1/shipments/packages?page=2&per_page=20

// Response
{
  "data": [...],
  "pagination": {
    "page": 2,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

**After (Cursor-Based):**
```javascript
// Request
GET /api/v1/shipments/packages?cursor=eyJsYXN0X2lkIjoiMTIzNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wIiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoibmV4dCIsImxpbWl0IjoyMH0=&limit=20

// Response
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJsYXN0X2lkIjoiNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wLTEyMzQ1Njc4OTAiLCJsYXN0X3VwZGF0ZWQiOiIyMDI0LTAzLTEzVDExOjAwOjAwWiIsImZpbHRlcnMiOnt9LCJkaXJlY3Rpb24iOiJuZXh0IiwibGltaXQiOjIwfQ==",
    "prev_cursor": "eyJsYXN0X2lkIjoiMTIzNDU2Nzg5MC1hYmNkLWVmZ2gtaWprbC1tbm9wIiwibGFzdF91cGRhdGVkIjoiMjAyNC0wMy0xM1QxMDozMDowMFoiLCJmaWx0ZXJzIjp7fSwiZGlyZWN0aW9uIjoicHJldiIsImxpbWl0IjoyMH0=",
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