# Bookings API Documentation

This document describes the API endpoints for the booking system, which allows users to create and manage booking links for scheduling meetings.

## Base URL

```
/api/v1/bookings
```

## Authentication

Most endpoints require authentication. Include your authentication token in the request headers:

```
Authorization: Bearer <your-token>
```

## Endpoints

### Health Check

#### GET `/health`

Check if the bookings service is running.

**Response:**
```json
{
  "status": "healthy",
  "service": "bookings"
}
```

### Public Endpoints (No Authentication Required)

#### GET `/public/{token}`

Get metadata for a public booking link.

**Parameters:**
- `token` (path): The booking link token (starts with `bl_` or `ot_`)

**Response:**
```json
{
  "data": {
    "title": "Coffee Chat",
    "description": "Book a 30-minute coffee chat",
    "template_questions": [
      {
        "id": "name",
        "label": "Your Name",
        "required": true,
        "type": "text"
      },
      {
        "id": "email",
        "label": "Email Address",
        "required": true,
        "type": "email"
      }
    ],
    "duration_options": [15, 30, 60, 120],
    "is_active": true
  }
}
```

#### GET `/public/{token}/availability`

Get available time slots for a booking link.

**Parameters:**
- `token` (path): The booking link token
- `duration` (query): Meeting duration in minutes (default: 30)

**Response:**
```json
{
  "data": {
    "slots": [
      {
        "start": "2024-01-20T10:00:00Z",
        "end": "2024-01-20T10:30:00Z",
        "available": true
      }
    ],
    "duration": 30,
    "timezone": "UTC"
  }
}
```

#### POST `/public/{token}/book`

Create a booking from a public link.

**Parameters:**
- `token` (path): The booking link token

**Request Body:**
```json
{
  "start": "2024-01-20T10:00:00Z",
  "end": "2024-01-20T10:30:00Z",
  "attendeeEmail": "guest@example.com",
  "answers": {
    "name": "John Doe",
    "email": "john@example.com",
    "company": "Acme Corp"
  }
}
```

**Response:**
```json
{
  "data": {
    "id": "booking-uuid",
    "message": "Booking created successfully",
    "calendar_event_id": "event-uuid"
  }
}
```

### Owner Endpoints (Authentication Required)

#### POST `/links`

Create a new evergreen booking link.

**Request Body:**
```json
{
  "title": "Coffee Chat",
  "description": "30-minute coffee chat",
  "duration": 30,
  "buffer_before": 5,
  "buffer_after": 5,
  "max_per_day": 3,
  "max_per_week": 10,
  "advance_days": 1,
  "max_advance_days": 30
}
```

**Response:**
```json
{
  "data": {
    "id": "link-uuid",
    "slug": "coffee-chat-abc123",
    "public_url": "/public/bookings/coffee-chat-abc123",
    "message": "Booking link created successfully"
  }
}
```

#### GET `/links`

List all booking links for the authenticated user.

**Response:**
```json
{
  "data": [
    {
      "id": "link-uuid",
      "title": "Coffee Chat",
      "slug": "coffee-chat-abc123",
      "is_active": true,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### GET `/links/{link_id}`

Get a specific booking link.

**Parameters:**
- `link_id` (path): The ID of the booking link

**Response:**
```json
{
  "data": {
    "id": "link-uuid",
    "title": "Coffee Chat",
    "slug": "coffee-chat-abc123",
    "is_active": true,
    "settings": {
      "duration": 30,
      "buffer_before": 5,
      "buffer_after": 5
    }
  }
}
```

#### PATCH `/links/{link_id}`

Update a booking link's settings.

**Parameters:**
- `link_id` (path): The ID of the booking link

**Request Body:**
```json
{
  "title": "Updated Coffee Chat",
  "settings": {
    "duration": 45
  }
}
```

**Response:**
```json
{
  "data": {
    "id": "link-uuid",
    "title": "Updated Coffee Chat",
    "settings": {
      "duration": 45
    }
  },
  "message": "Booking link updated successfully"
}
```

#### POST `/links/{link_id}:duplicate`

Duplicate an existing booking link.

**Parameters:**
- `link_id` (path): The ID of the booking link to duplicate

**Response:**
```json
{
  "data": {
    "id": "new-link-uuid",
    "slug": "coffee-chat-abc123_copy_xyz",
    "message": "Booking link duplicated successfully"
  }
}
```

#### POST `/links/{link_id}:toggle`

Toggle a booking link's active status.

**Parameters:**
- `link_id` (path): The ID of the booking link

**Response:**
```json
{
  "data": {
    "id": "link-uuid",
    "is_active": false,
    "message": "Booking link deactivated successfully"
  }
}
```

#### POST `/links/{link_id}/one-time`

Create a one-time link for a specific recipient.

**Parameters:**
- `link_id` (path): The ID of the parent booking link

**Request Body:**
```json
{
  "recipient_email": "guest@example.com",
  "recipient_name": "John Doe",
  "expires_in_days": 7
}
```

**Response:**
```json
{
  "data": {
    "token": "ot_abc123def456",
    "public_url": "/public/bookings/ot_abc123def456",
    "expires_at": "2024-01-22T10:00:00Z",
    "message": "One-time link created successfully"
  }
}
```

#### GET `/links/{link_id}/analytics`

Get analytics for a specific booking link.

**Parameters:**
- `link_id` (path): The ID of the booking link

**Response:**
```json
{
  "data": {
    "link_id": "link-uuid",
    "views": 142,
    "bookings": 12,
    "conversion_rate": "8.5%",
    "last_viewed": "2024-01-19T15:30:00Z",
    "top_referrers": ["Direct", "Email", "LinkedIn"],
    "recent_activity": [
      {
        "type": "view",
        "timestamp": "2024-01-19T15:30:00Z"
      }
    ]
  }
}
```

## Error Responses

All endpoints return standard HTTP status codes and error messages:

### 400 Bad Request
```json
{
  "detail": "Missing required field: attendeeEmail"
}
```

### 404 Not Found
```json
{
  "detail": "Booking link not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Public endpoints**: 100-200 requests per hour per IP
- **Owner endpoints**: 50-100 requests per hour per user
- **Booking creation**: 10 requests per hour per IP

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642608000
```

## Security Features

- **Token validation**: All tokens are validated for format and expiration
- **Input sanitization**: User inputs are sanitized to prevent injection attacks
- **Audit logging**: All actions are logged for security monitoring
- **Rate limiting**: Prevents abuse and DoS attacks

## Usage Examples

### Creating a Booking Link

```bash
curl -X POST "https://api.example.com/api/v1/bookings/links" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Coffee Chat",
    "description": "30-minute coffee chat",
    "duration": 30
  }'
```

### Creating a One-Time Link

```bash
curl -X POST "https://api.example.com/api/v1/bookings/links/<link-id>/one-time" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "recipient_email": "guest@example.com",
    "recipient_name": "John Doe",
    "expires_in_days": 7
  }'
```

### Getting Available Slots

```bash
curl "https://api.example.com/api/v1/bookings/public/<token>/availability?duration=30"
```

### Creating a Booking

```bash
curl -X POST "https://api.example.com/api/v1/bookings/public/<token>/book" \
  -H "Content-Type: application/json" \
  -d '{
    "start": "2024-01-20T10:00:00Z",
    "end": "2024-01-20T10:30:00Z",
    "attendeeEmail": "guest@example.com",
    "answers": {
      "name": "John Doe",
      "email": "john@example.com"
    }
  }'
```

## Support

For questions or issues with the API, please contact the development team or refer to the internal documentation.
