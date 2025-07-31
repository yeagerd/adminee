# Microsoft Email Threading Implementation

## Problem Statement

The current email threading implementation relies on Microsoft Graph API's `conversationId` field, which doesn't work reliably for grouping emails into threads. Users see individual emails instead of properly grouped threads (e.g., seeing 1 email instead of 3 in a thread that should contain multiple emails).

## Root Cause Analysis

- **Microsoft Graph API's `conversationId`** is more like a "conversation topic" rather than a strict thread grouping
- **Emails in the same thread** can have different `conversationId` values
- **Microsoft's threading logic** differs significantly from Gmail's `threadId` approach
- **Frontend smart threading** attempts (subject-based grouping) are unreliable

## Solution: Microsoft Graph Threading API

Microsoft Graph provides dedicated threading APIs that properly group emails into conversations/threads. We need to implement these APIs to get accurate thread information.

## Design Overview

### Architecture Changes

1. **Backend: New Microsoft Graph Threading Endpoints**
   - Add Microsoft Graph conversation/thread API calls
   - Create new unified threading endpoints
   - Modify email fetching to include thread information

2. **Frontend: Thread-Aware Email Display**
   - Fetch thread information when needed
   - Merge thread data with email data
   - Implement thread-based email grouping

### API Design

#### New Backend Endpoints

```
GET /api/v1/email/threads
- Get all threads for a user
- Parameters: providers, limit, offset, folder_id, labels

GET /api/v1/email/threads/{thread_id}
- Get specific thread with all emails
- Parameters: include_body, no_cache

GET /api/v1/email/messages/{message_id}/thread
- Get thread for a specific message
- Parameters: include_body, no_cache
```

#### Microsoft Graph API Integration

```
GET /me/mailFolders/{folder-id}/messages?$expand=conversation
GET /me/messages?$expand=conversation
GET /me/conversations/{conversation-id}/messages
```

## Implementation Tasks

### Backend Tasks

#### Microsoft Graph Client Updates
- [ ] Add `get_conversations()` method to MicrosoftAPIClient
- [ ] Add `get_conversation_messages(conversation_id)` method
- [ ] Add `get_message_conversation(message_id)` method
- [ ] Update `get_messages()` to include conversation expansion
- [ ] Add conversation caching support

#### New API Endpoints
- [ ] Create `/email/threads` endpoint in `services/office/api/email.py`
- [ ] Create `/email/threads/{thread_id}` endpoint
- [ ] Create `/email/messages/{message_id}/thread` endpoint
- [ ] Add thread-specific caching logic
- [ ] Implement thread pagination support

#### Data Models and Schemas
- [ ] Create `EmailThread` schema in `services/office/schemas/__init__.py`
- [ ] Create `Conversation` schema for Microsoft Graph responses
- [ ] Update `EmailMessage` schema to include thread information
- [ ] Add thread-related response models

#### Threading Logic
- [ ] Implement Microsoft conversation to thread mapping
- [ ] Create thread normalization logic (similar to email normalization)
- [ ] Add thread ID generation and management
- [ ] Implement thread merging logic for cross-provider support

#### Caching and Performance
- [ ] Add thread-level caching in `cache_manager.py`
- [ ] Implement thread cache invalidation logic
- [ ] Add thread fetch optimization (batch requests)
- [ ] Create thread cache warming strategies

### Frontend Tasks

#### Gateway Client Updates
- [ ] Add `getThreads()` method to `GatewayClient`
- [ ] Add `getThread(threadId)` method
- [ ] Add `getMessageThread(messageId)` method
- [ ] Update `getEmails()` to optionally include thread information

#### Email View Component Updates
- [ ] Modify `EmailView` to use thread-based fetching
- [ ] Update thread selection logic to use thread IDs
- [ ] Implement thread-aware email grouping
- [ ] Add thread loading states and error handling

#### Thread Display Components
- [ ] Update `EmailThread` component to handle thread data
- [ ] Modify `EmailListCard` to show thread information
- [ ] Update `EmailThreadCard` for thread context
- [ ] Add thread navigation and breadcrumbs

#### State Management
- [ ] Add thread state management to `EmailView`
- [ ] Implement thread selection and navigation
- [ ] Add thread caching on frontend
- [ ] Update URL routing for thread views

### Testing Tasks

#### Backend Testing
- [ ] Unit tests for Microsoft Graph threading methods
- [ ] Integration tests for new API endpoints
- [ ] Test thread caching and invalidation
- [ ] Performance tests for thread fetching

#### Frontend Testing
- [ ] Unit tests for thread-aware components
- [ ] Integration tests for thread navigation
- [ ] Test thread state management
- [ ] Performance tests for thread rendering

#### End-to-End Testing
- [ ] Test complete thread workflow
- [ ] Test cross-provider thread handling
- [ ] Test thread caching behavior
- [ ] Test error handling and edge cases

### Documentation Tasks

- [ ] Update API documentation for new endpoints
- [ ] Document thread data models and schemas
- [ ] Create thread implementation guide
- [ ] Update frontend component documentation
- [ ] Document caching strategies and performance considerations

## Implementation Phases

### Phase 1: Backend Foundation (Week 1)
- [ ] Microsoft Graph client threading methods
- [ ] Basic thread API endpoints
- [ ] Thread data models and schemas
- [ ] Initial caching implementation

### Phase 2: Frontend Integration (Week 2)
- [ ] Gateway client threading methods
- [ ] Email view thread integration
- [ ] Thread component updates
- [ ] Basic thread navigation

### Phase 3: Polish and Testing (Week 3)
- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Error handling improvements
- [ ] Documentation updates

## Success Criteria

- [ ] Microsoft emails properly grouped into threads
- [ ] Thread navigation works correctly (one-pane and two-pane modes)
- [ ] Performance remains acceptable (thread fetching < 2s)
- [ ] Cross-provider threading works (Gmail + Microsoft)
- [ ] Thread caching reduces API calls
- [ ] Error handling gracefully degrades

## Risk Mitigation

### Technical Risks
- **Microsoft Graph API limitations**: Implement fallback to current approach
- **Performance degradation**: Add aggressive caching and optimization
- **Rate limiting**: Implement request throttling and retry logic

### Implementation Risks
- **Complexity**: Break implementation into smaller, testable phases
- **Backward compatibility**: Maintain existing API endpoints during transition
- **Data consistency**: Implement proper cache invalidation and sync

## Future Enhancements

- [ ] Real-time thread updates via webhooks
- [ ] Advanced thread filtering and search
- [ ] Thread analytics and insights
- [ ] Cross-provider thread merging improvements
- [ ] Thread-based email actions (archive entire thread, etc.) 