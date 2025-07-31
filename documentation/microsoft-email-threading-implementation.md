# Microsoft Email Threading Implementation

## Overview

This document describes the implementation of Microsoft email threading functionality in the Briefly platform. The implementation addresses the problem where Microsoft Graph API's `conversationId` field doesn't reliably group emails into threads, causing users to see individual emails instead of properly grouped conversations.

## Architecture

### Backend Components

#### 1. Microsoft Graph Client Extensions (`services/office/core/clients/microsoft.py`)

The `MicrosoftAPIClient` class has been extended with new methods for thread-aware email fetching:

- `get_conversations()` - Fetch list of email conversations/threads
- `get_conversation_messages(conversation_id)` - Get messages in a specific conversation
- `get_message_conversation(message_id)` - Get conversation for a specific message
- `get_messages_with_conversation()` - Get messages with conversation expansion

#### 2. Thread API Endpoints (`services/office/api/email.py`)

New REST API endpoints for thread operations:

- `GET /api/v1/email/threads` - Get email threads from multiple providers
- `GET /api/v1/email/threads/{thread_id}` - Get a specific thread with all messages
- `GET /api/v1/email/messages/{message_id}/thread` - Get thread containing a specific message

#### 3. Thread Normalization (`services/office/core/normalizer.py`)

Functions to convert provider-specific thread data into unified format:

- `normalize_google_thread()` - Convert Gmail thread data
- `normalize_microsoft_conversation()` - Convert Microsoft conversation data
- `merge_threads()` - Merge threads across providers
- `normalize_thread_id()` - Normalize thread IDs

#### 4. Thread Caching (`services/office/core/cache_manager.py`)

Thread-specific cache key generation functions:

- `generate_thread_cache_key()` - Cache key for individual threads
- `generate_threads_list_cache_key()` - Cache key for thread lists
- `generate_message_thread_cache_key()` - Cache key for message threads

### Frontend Components

#### 1. Gateway Client Extensions (`frontend/lib/gateway-client.ts`)

New methods in the `GatewayClient` class:

- `getThreads()` - Fetch email threads
- `getThread(threadId)` - Fetch specific thread
- `getMessageThread(messageId)` - Fetch thread for a message

#### 2. Thread Components (`frontend/components/email/`)

- `EmailThread` - Display a single thread with all messages
- `EmailThreadList` - Display list of threads with selection
- `EmailThreadCard` - Individual message within a thread

#### 3. Thread State Management (`frontend/hooks/use-threads.ts`)

Custom React hook for managing thread state:

- Thread fetching and caching
- Thread selection and navigation
- Error handling and loading states

## API Reference

### Get Email Threads

```http
GET /api/v1/email/threads
```

**Query Parameters:**
- `providers` (array) - Providers to fetch from (google, microsoft)
- `limit` (number) - Maximum threads per provider (1-200, default: 50)
- `include_body` (boolean) - Include message body content (default: false)
- `labels` (array) - Filter by labels (inbox, sent, etc.)
- `folder_id` (string) - Folder ID to fetch from
- `q` (string) - Search query
- `page_token` (string) - Pagination token
- `no_cache` (boolean) - Bypass cache (default: false)

**Response:**
```json
{
  "success": true,
  "data": {
    "threads": [
      {
        "id": "gmail_thread123",
        "subject": "Project Discussion",
        "messages": [...],
        "participant_count": 3,
        "last_message_date": "2024-01-15T10:30:00Z",
        "is_read": false,
        "providers": ["google"]
      }
    ],
    "total_count": 25,
    "providers_used": ["google", "microsoft"],
    "provider_errors": null,
    "has_more": true
  },
  "cache_hit": false,
  "provider_used": "google",
  "request_id": "req_123"
}
```

### Get Specific Thread

```http
GET /api/v1/email/threads/{thread_id}
```

**Path Parameters:**
- `thread_id` - Thread ID in format "provider_originalId" (e.g., "gmail_thread123")

**Query Parameters:**
- `include_body` (boolean) - Include message body content (default: true)
- `no_cache` (boolean) - Bypass cache (default: false)

**Response:**
```json
{
  "success": true,
  "data": {
    "thread": {
      "id": "gmail_thread123",
      "subject": "Project Discussion",
      "messages": [
        {
          "id": "gmail_msg1",
          "subject": "Project Discussion",
          "from_address": {"email": "sender@example.com", "name": "John Doe"},
          "to_addresses": [{"email": "recipient@example.com", "name": "Jane Smith"}],
          "date": "2024-01-15T10:00:00Z",
          "body_text": "Let's discuss the project...",
          "is_read": true,
          "provider": "google"
        }
      ],
      "participant_count": 3,
      "last_message_date": "2024-01-15T10:30:00Z",
      "is_read": false,
      "providers": ["google"]
    },
    "provider_used": "google"
  },
  "cache_hit": false,
  "request_id": "req_123"
}
```

### Get Message Thread

```http
GET /api/v1/email/messages/{message_id}/thread
```

**Path Parameters:**
- `message_id` - Message ID in format "provider_originalId" (e.g., "gmail_msg1")

**Query Parameters:**
- `include_body` (boolean) - Include message body content (default: true)
- `no_cache` (boolean) - Bypass cache (default: false)

## Frontend Usage

### Using the Thread Hook

```typescript
import { useThreads } from '@/hooks/use-threads';

function EmailView() {
  const {
    threads,
    selectedThread,
    selectedMessageId,
    loading,
    error,
    hasMore,
    fetchThreads,
    selectThread,
    selectMessage,
    refreshThreads
  } = useThreads({
    providers: ['google', 'microsoft'],
    limit: 50,
    includeBody: false,
    autoFetch: true
  });

  if (loading) return <div>Loading threads...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <EmailThreadList
        threads={threads}
        selectedThreadId={selectedThread?.id}
        selectedMessageId={selectedMessageId}
        onSelectThread={selectThread}
        onSelectMessage={selectMessage}
      />
    </div>
  );
}
```

### Using Thread Components

```typescript
import EmailThread from '@/components/email/email-thread';
import EmailThreadList from '@/components/email/email-thread-list';

// Display a single thread
function ThreadView({ thread }) {
  return (
    <EmailThread
      thread={thread}
      onSelectMessage={(messageId) => console.log('Selected:', messageId)}
      selectedMessageId="gmail_msg1"
    />
  );
}

// Display a list of threads
function ThreadListView({ threads }) {
  return (
    <EmailThreadList
      threads={threads}
      selectedThreadId="gmail_thread123"
      onSelectThread={(threadId) => console.log('Selected thread:', threadId)}
      showReadingPane={true}
    />
  );
}
```

## Thread ID Format

Thread IDs follow a unified format: `provider_originalId`

Examples:
- `gmail_thread123` - Gmail thread with ID "thread123"
- `microsoft_conv456` - Microsoft conversation with ID "conv456"
- `google_thread789` - Gmail thread with ID "thread789" (alternative prefix)

## Caching Strategy

### Cache Keys

Thread data is cached using provider-specific keys:

- Thread lists: `office:{user_id}:threads:providers,{providers}:limit,{limit}:...`
- Individual threads: `office:{user_id}:thread:thread_id:with_body`
- Message threads: `office:{user_id}:message_thread:message_id:with_body`

### Cache TTL

- Thread lists: 5 minutes
- Individual threads: 10 minutes
- Message threads: 10 minutes

### Cache Invalidation

Thread caches are invalidated when:
- New messages are received
- Thread status changes (read/unread)
- User refreshes data

## Error Handling

### Common Errors

1. **Provider Connection Issues**
   ```json
   {
     "success": false,
     "error": {
       "message": "Failed to create API client for provider microsoft"
     }
   }
   ```

2. **Thread Not Found**
   ```json
   {
     "success": false,
     "error": {
       "message": "Thread gmail_thread123 not found"
     }
   }
   ```

3. **Invalid Thread ID Format**
   ```json
   {
     "success": false,
     "error": {
       "message": "Invalid thread ID format: invalid_id. Expected format: 'provider_originalId'"
     }
   }
   ```

### Fallback Behavior

When Microsoft Graph threading fails:
1. Fall back to individual message fetching
2. Use subject-based grouping as backup
3. Log errors for monitoring
4. Return partial results when possible

## Performance Considerations

### Optimization Strategies

1. **Batch Requests**: Fetch multiple threads in parallel
2. **Selective Body Loading**: Only load message bodies when needed
3. **Caching**: Aggressive caching with appropriate TTL
4. **Pagination**: Support for large thread lists
5. **Provider Parallelism**: Fetch from multiple providers simultaneously

### Performance Targets

- Thread list fetching: < 2 seconds
- Individual thread loading: < 1 second
- Message thread resolution: < 1 second
- Cache hit ratio: > 80%

## Testing

### Backend Tests

Run the threading tests:

```bash
cd services/office
python -m pytest tests/test_email_threading.py -v
```

### Frontend Tests

Test the thread components:

```bash
cd frontend
npm test -- --testPathPattern=email-thread
```

## Monitoring

### Key Metrics

1. **Thread Fetch Performance**
   - Average response time
   - Cache hit ratio
   - Error rates by provider

2. **Thread Quality**
   - Thread grouping accuracy
   - Cross-provider merge success rate
   - User satisfaction metrics

3. **API Usage**
   - Request volume by endpoint
   - Provider-specific usage
   - Rate limiting events

### Logging

Thread operations are logged with:
- Request ID for tracing
- Provider information
- Performance metrics
- Error details

## Future Enhancements

### Planned Features

1. **Real-time Updates**
   - WebSocket-based thread updates
   - Live thread synchronization

2. **Advanced Threading**
   - Machine learning-based thread grouping
   - Improved cross-provider merging
   - Thread analytics and insights

3. **Thread Actions**
   - Archive entire threads
   - Bulk thread operations
   - Thread-based email actions

4. **Performance Improvements**
   - Background thread prefetching
   - Intelligent cache warming
   - Optimized API calls

## Troubleshooting

### Common Issues

1. **Threads Not Grouping**
   - Check provider API permissions
   - Verify conversation ID mapping
   - Review normalization logic

2. **Slow Performance**
   - Monitor cache hit rates
   - Check provider API response times
   - Review batch request optimization

3. **Missing Messages**
   - Verify message permissions
   - Check thread ID parsing
   - Review error handling

### Debug Mode

Enable debug logging:

```python
# Backend
import logging
logging.getLogger('services.office.api.email').setLevel(logging.DEBUG)

# Frontend
localStorage.setItem('debug', 'email-threading:*');
```

## Support

For issues with the threading implementation:

1. Check the logs for error details
2. Verify provider API connectivity
3. Test with minimal thread data
4. Review cache state and invalidation
5. Contact the development team with request IDs 