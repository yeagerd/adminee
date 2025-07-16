# Frontend Prototype Implementation Tasks

## Overview
This document outlines the incremental implementation plan for building out the prototype design in the `frontend/` directory. The prototype demonstrates a modern 3-pane layout with AI-powered productivity features.  There is a v0.dev prototype in /Users/yeagerd/github/prototype for reference, which you shall not modify.

## Phase 0: Integration Streamlining

### Task 0.1: Streamline Provider-Based Integrations
**Priority**: Critical
**Estimated Time**: 3-5 days
**Dependencies**: None

**Description**: Streamline integrations to be Microsoft OR Google based on user's login provider
- [x] Analyze current integration patterns in user service and office service
- [x] Implement provider detection based on OAuth login (Microsoft vs Google)
- [x] Update integration configuration to only show relevant provider options
- [x] Modify office service to route API calls to correct provider
- [x] Update frontend integration UI to show only available provider
- [x] Add provider-specific feature flags and capabilities
- [x] Update authentication flow to capture and store provider preference
- [x] Add provider switching logic (if user wants to change providers)
- [x] Update API clients to use provider-specific endpoints
- [x] Add provider validation and error handling

**Files to Create/Modify**:
- `services/user/auth/nextauth.py` (update provider handling)
- `services/user/models/integration.py` (add provider field)
- `services/user/schemas/integration.py` (update schemas)
- `services/office/core/api_client_factory.py` (provider routing)
- `services/office/core/clients/google.py` (ensure Google-only features)
- `services/office/core/clients/microsoft.py` (ensure Microsoft-only features)
- `frontend/lib/auth.ts` (provider detection)
- `frontend/lib/api-client.ts` (provider-specific routing)
- `frontend/app/integrations/page.tsx` (show only relevant provider)
- `frontend/components/auth/oauth-buttons.tsx` (provider selection)
- `frontend/types/next-auth.d.ts` (add provider types)

**Benefits**:
- Simplified user experience (no confusion about which integrations to use)
- Reduced complexity in API routing and error handling
- Better performance (no unnecessary API calls to unused provider)
- Cleaner codebase with provider-specific implementations
- Easier testing and debugging

## Phase 1: Core Layout Foundation

### Task 1.1: Implement 3-Pane Layout Structure
**Priority**: High
**Estimated Time**: 2-3 days
**Dependencies**: None

**Description**: Create the foundational 3-pane layout structure
- [x] Create new layout component with sidebar, main pane, and draft pane
- [x] Implement responsive sidebar with collapsible functionality
- [x] Set up main content area with proper overflow handling
- [x] Add right-side draft pane with resizable functionality
- [x] Ensure proper flex layout and responsive behavior

**Files to Create/Modify**:
- `frontend/components/layout/app-layout.tsx`
- `frontend/components/layout/sidebar.tsx`
- `frontend/components/layout/main-pane.tsx`
- `frontend/components/layout/draft-pane.tsx`
- `frontend/app/dashboard/page.tsx` (update existing)

## Phase 2: Navigation and Tool Switching

### Task 2.1: Implement Sidebar Navigation
**Priority**: High
**Estimated Time**: 1-2 days
**Dependencies**: Task 1.1

**Description**: Create the left sidebar with tool navigation
- [x] Implement tool navigation with icons and labels
- [x] Add active state styling and transitions
- [x] Include "Soon" badges for future features
- [x] Add collapsible functionality for focus mode
- [x] Ensure proper accessibility and keyboard navigation

**Files to Create/Modify**:
- `frontend/components/navigation/sidebar-nav.tsx`
- `frontend/types/navigation.ts`
- `frontend/hooks/use-navigation.ts`

### Task 2.2: Implement Tool State Management
**Priority**: Medium
**Estimated Time**: 1 day
**Dependencies**: Task 2.1

**Description**: Set up state management for tool switching
- [x] Create tool state management with React context
- [x] Implement tool switching logic
- [x] Add URL routing for deep linking to tools
- [x] Include tool-specific settings and preferences
- [x] Add tool state persistence

**Files to Create/Modify**:
- `frontend/contexts/tool-context.tsx`
- `frontend/hooks/use-tool-state.ts`
- `frontend/lib/tool-routing.ts`

## Phase 3: Core Tool Views

### Task 3.1: Implement Calendar View
**Priority**: High
**Estimated Time**: 3-4 days
**Dependencies**: Task 1.1, Task 2.1

**Description**: Create the calendar interface visually similar to Google/Microsoft's web calendar view, with AI integration
- [ ] Implement day/week/month view toggles
- [ ] Create event cards with organizer status indicators
- [ ] Add external attendee and acceptance count displays
- [ ] Include inline AI suggestions for events
- [ ] Add event creation and editing capabilities
- [ ] Integrate with existing calendar components

**Files to Create/Modify**:
- `frontend/components/views/calendar-view.tsx`
- `frontend/components/calendar/event-card.tsx`
- `frontend/components/calendar/view-toggle.tsx`
- `frontend/components/calendar/ai-suggestions.tsx`
- Update existing `frontend/components/calendar-event-item.tsx`

### Task 3.2: Implement Email View
**Priority**: High
**Estimated Time**: 3-4 days
**Dependencies**: Task 1.1, Task 2.1

**Description**: Create the email interface with AI features
- [ ] Implement threaded email display
- [ ] Add email cards with priority indicators
- [ ] Include calendar relevance and package tracking flags
- [ ] Add AI-generated summaries and draft reply buttons
- [ ] Implement email composition and reply functionality
- [ ] Add email filtering and search capabilities

**Files to Create/Modify**:
- `frontend/components/views/email-view.tsx`
- `frontend/components/email/email-card.tsx`
- `frontend/components/email/email-thread.tsx`
- `frontend/components/email/ai-summary.tsx`
- `frontend/components/email/email-filters.tsx`

### Task 3.3: Implement Documents View
**Priority**: Medium
**Estimated Time**: 2-3 days
**Dependencies**: Task 1.1, Task 2.1

**Description**: Create the documents interface
- [ ] Implement document list/card view toggle
- [ ] Add document cards with source indicators (Drive, OneNote, Notion)
- [ ] Include AI-tagged topics and meeting relevance
- [ ] Add document filtering and search
- [ ] Implement document preview and sharing
- [ ] Add document creation capabilities

**Files to Create/Modify**:
- `frontend/components/views/documents-view.tsx`
- `frontend/components/documents/document-card.tsx`
- `frontend/components/documents/document-filters.tsx`
- `frontend/components/documents/document-preview.tsx`

### Task 3.4: Implement Tasks View
**Priority**: High
**Estimated Time**: 3-4 days
**Dependencies**: Task 1.1, Task 2.1

**Description**: Create the tasks/todos interface with AI integration
- [ ] Implement task list with drag-and-drop reordering
- [ ] Add task cards with priority, due date, and status indicators
- [ ] Include AI-suggested task categorization and prioritization
- [ ] Add task creation with natural language input
- [ ] Implement task filtering by status, priority, and due date
- [ ] Add task completion tracking and progress indicators
- [ ] Include calendar integration for task scheduling
- [ ] Add bulk task operations (complete, delete, move)
- [ ] Implement task templates and recurring tasks
- [ ] Add task search and quick actions

**Files to Create/Modify**:
- `frontend/components/views/tasks-view.tsx`
- `frontend/components/tasks/task-card.tsx`
- `frontend/components/tasks/task-list.tsx`
- `frontend/components/tasks/task-filters.tsx`
- `frontend/components/tasks/task-creator.tsx`
- `frontend/components/tasks/task-progress.tsx`
- `frontend/components/tasks/ai-suggestions.tsx`
- `frontend/hooks/use-tasks.ts`
- `frontend/lib/task-utils.ts`

## Phase 4: Advanced Tool Views

### Task 4.1: Implement Package Tracker View
**Priority**: Medium
**Estimated Time**: 2-3 days
**Dependencies**: Task 1.1, Task 2.1

**Description**: Create the package tracking interface
- [ ] Implement package table with carrier and status
- [ ] Add tracking number display and clickable links
- [ ] Include ETA and location information
- [ ] Add calendar integration for delivery dates
- [ ] Implement package search and filtering
- [ ] Add manual package entry functionality

**Files to Create/Modify**:
- `frontend/components/views/packages-view.tsx`
- `frontend/components/packages/package-table.tsx`
- `frontend/components/packages/package-card.tsx`
- `frontend/components/packages/tracking-link.tsx`

### Task 4.2: Implement Research Assistant View
**Priority**: High
**Estimated Time**: 4-5 days
**Dependencies**: Task 1.1, Task 2.1

**Description**: Create the AI-powered research interface
- [ ] Implement split-pane layout (results + document)
- [ ] Add search results with source categorization
- [ ] Include collapsible result sections
- [ ] Create interactive research document editor
- [ ] Add export to Drive/OneNote/Notion functionality
- [ ] Implement query history and saved searches

**Files to Create/Modify**:
- `frontend/components/views/research-view.tsx`
- `frontend/components/research/search-results.tsx`
- `frontend/components/research/research-document.tsx`
- `frontend/components/research/result-section.tsx`
- `frontend/components/research/export-options.tsx`

### Task 4.3: Implement Pulse (News) View
**Priority**: Medium
**Estimated Time**: 3-4 days
**Dependencies**: Task 1.1, Task 2.1

**Description**: Create the industry news feed interface
- [ ] Implement news feed with article cards
- [ ] Add category filtering (AI, Pharma, Fintech, etc.)
- [ ] Include trending indicators and read time
- [ ] Add "Add to Research" and "Draft Email" actions
- [ ] Implement source following and keyword tracking
- [ ] Add news summarization and sharing features

**Files to Create/Modify**:
- `frontend/components/views/pulse-view.tsx`
- `frontend/components/pulse/news-card.tsx`
- `frontend/components/pulse/category-filters.tsx`
- `frontend/components/pulse/trending-indicator.tsx`
- `frontend/components/pulse/news-actions.tsx`

## Phase 5: Draft Pane and AI Integration

### Task 5.1: Implement Core Draft Pane Structure
**Priority**: High
**Estimated Time**: 1-2 days
**Dependencies**: Task 1.1

**Description**: Create the foundational draft pane structure with type switching and basic UI
- [x] Create draft pane container with proper layout
- [x] Implement draft type switcher (email, calendar, document)
- [x] Add draft metadata forms (context-dependent fields)
- [x] Create basic draft actions (Send/Create, Discard)
- [x] Add AI-generated content indicators
- [x] Implement draft state management

**Files to Create/Modify**:
- `frontend/components/draft/draft-pane.tsx`
- `frontend/components/draft/draft-type-switcher.tsx`
- `frontend/components/draft/draft-metadata.tsx`
- `frontend/components/draft/draft-actions.tsx`
- `frontend/components/draft/ai-indicator.tsx`
- `frontend/hooks/use-draft-state.ts`
- `frontend/types/draft.ts`

### Task 5.2: Implement Rich Text Editor Integration
**Priority**: High
**Estimated Time**: 2-3 days
**Dependencies**: Task 5.1

**Description**: Integrate TipTap rich text editor with markdown support and document-specific features
- [x] Install and configure TipTap editor
- [x] Create document-specific editor with markdown support
- [x] Implement email editor with recipient fields
- [x] Add calendar editor with date/time pickers
- [x] Create editor toolbar with formatting options
- [x] Add auto-save functionality
- [x] Implement content validation and error handling

**Files to Create/Modify**:
- `frontend/components/draft/draft-editor.tsx`
- `frontend/components/draft/editors/document-editor.tsx`
- `frontend/components/draft/editors/email-editor.tsx`
- `frontend/components/draft/editors/calendar-editor.tsx`
- `frontend/components/draft/editor-toolbar.tsx`
- `frontend/hooks/use-editor.ts`
- `frontend/lib/editor-config.ts`
- `package.json` (add TipTap dependencies)

### Task 5.3: Implement Backend Draft Storage
**Priority**: High
**Estimated Time**: 2-3 days
**Dependencies**: None

**Description**: Extend chat service to support persistent user draft storage
- [x] Add user draft models to chat service database
- [x] Create draft CRUD endpoints (create, read, update, delete)
- [x] Implement draft list retrieval by user_id
- [x] Add draft type validation and constraints
- [x] Extend existing draft functions to support user drafts
- [x] Add draft metadata storage (subject, recipients, dates, etc.)
- [x] Implement draft versioning and history

**Files to Create/Modify**:
- `services/chat/models.py` (add UserDraft model)
- `services/chat/api.py` (add draft endpoints)
- `services/chat/agents/llm_tools.py` (extend draft functions)
- `services/chat/history_manager.py` (add user draft functions)
- `services/chat/schemas.py` (add draft schemas)

### Task 5.4: Implement Draft List and Navigation
**Priority**: Medium
**Estimated Time**: 1-2 days
**Dependencies**: Task 5.3

**Description**: Add draft list view accessible from sidebar with filtering and management
- [x] Add "Drafts" to navigation types and sidebar
- [x] Create draft list view with cards and previews
- [x] Implement draft filtering by type, status, and date
- [x] Add new draft creation flow with type selection
- [x] Create draft search functionality
- [x] Add draft bulk operations (delete, archive)
- [x] Implement draft sorting and organization

**Files to Create/Modify**:
- `frontend/types/navigation.ts` (add drafts tool)
- `frontend/components/layout/sidebar.tsx` (add drafts nav item)
- `frontend/components/drafts/drafts-list.tsx`
- `frontend/components/drafts/draft-card.tsx`
- `frontend/components/drafts/draft-filters.tsx`
- `frontend/components/drafts/new-draft-button.tsx`
- `frontend/hooks/use-drafts.ts`
- `frontend/lib/draft-utils.ts`

### Task 5.5: Implement Draft Actions and Integration
**Priority**: High
**Estimated Time**: 2-3 days
**Dependencies**: Task 5.2, Task 5.3

**Description**: Connect draft actions to office service and implement send/create functionality
- [x] Implement email sending via office service
- [x] Add calendar event creation via office service
- [x] Create document saving to Google Drive/OneDrive
- [x] Add draft discard functionality with confirmation
- [x] Implement draft auto-save and recovery
- [x] Add draft sharing and collaboration features
- [x] Create draft templates and quick actions

**Files to Create/Modify**:
- `frontend/components/draft/draft-actions.tsx`
- `frontend/services/draft-service.ts`
- `frontend/lib/office-integration.ts`
- `frontend/hooks/use-draft-actions.ts`
- `frontend/components/draft/draft-templates.tsx`
- `frontend/components/draft/draft-recovery.tsx`

### Task 5.6: Implement AI Draft Integration
**Priority**: High
**Estimated Time**: 1-2 days
**Dependencies**: Task 5.1, Task 5.3

**Description**: Connect AI-generated drafts from chat service to draft pane
- [ ] Integrate with chat service draft endpoints
- [ ] Display AI-generated drafts in draft pane
- [ ] Add AI content indicators and styling
- [ ] Implement AI draft editing and modification
- [ ] Add AI draft approval and rejection flow
- [ ] Create AI draft suggestions and improvements
- [ ] Implement draft handoff between AI and user

**Files to Create/Modify**:
- `frontend/components/draft/ai-draft-indicator.tsx`
- `frontend/hooks/use-ai-drafts.ts`
- `frontend/services/ai-draft-service.ts`
- `frontend/components/draft/ai-suggestions.tsx`
- `frontend/lib/ai-draft-integration.ts`

### Task 5.7: Add Draft Analytics and Optimization
**Priority**: Low
**Estimated Time**: 1-2 days
**Dependencies**: Task 5.5

**Description**: Add draft analytics, performance optimization, and advanced features
- [ ] Implement draft usage analytics and metrics
- [ ] Add draft performance monitoring
- [ ] Create draft keyboard shortcuts and accessibility
- [ ] Implement draft offline support and sync
- [ ] Add draft export and backup functionality
- [ ] Create draft collaboration features
- [ ] Implement draft AI assistance and suggestions

**Files to Create/Modify**:
- `frontend/components/draft/draft-analytics.tsx`
- `frontend/hooks/use-draft-analytics.ts`
- `frontend/lib/draft-performance.ts`
- `frontend/components/draft/draft-shortcuts.tsx`
- `frontend/services/draft-sync.ts`

### Task 5.8: Implement AI Command Processing
**Priority**: High
**Estimated Time**: 2-3 days
**Dependencies**: Task 5.6

**Description**: Connect assistant bar to AI services for draft creation and management
- [ ] Implement command parsing and routing for drafts
- [ ] Add draft creation commands ("draft email to...", "create calendar event...")
- [ ] Include draft editing and modification commands
- [ ] Add research and document drafting commands
- [ ] Implement command history and suggestions
- [ ] Add error handling and fallbacks for draft commands
- [ ] Create voice input support for draft commands

**Files to Create/Modify**:
- `frontend/lib/ai-commands.ts`
- `frontend/hooks/use-ai-commands.ts`
- `frontend/services/ai-service.ts`
- `frontend/components/assistant/command-processor.tsx`
- `frontend/components/assistant/draft-commands.tsx`

## Phase 6: Integration and Polish

### Task 6.1: Integrate with Existing Services
**Priority**: High
**Estimated Time**: 3-4 days
**Dependencies**: Task 0.1, All previous phases

**Description**: Connect new UI with existing backend services
- [ ] Integrate with chat service for AI interactions
- [ ] Connect to office service for calendar/email (provider-specific)
- [ ] Integrate with user service for authentication (provider-aware)
- [ ] Add proper error handling and loading states
- [ ] Implement real-time updates where applicable
- [ ] Add proper TypeScript types for all integrations
- [ ] Ensure provider-specific API routing works correctly

**Files to Create/Modify**:
- `frontend/lib/api-integrations.ts`
- `frontend/hooks/use-services.ts`
- `frontend/types/api.ts`
- Update existing service clients

### Task 6.2: Implement Global Search
**Priority**: Medium
**Estimated Time**: 2-3 days
**Dependencies**: Task 6.3

**Description**: Add comprehensive global search functionality
- [ ] Implement search across all tools and data
- [ ] Add search result categorization
- [ ] Include keyboard navigation and shortcuts
- [ ] Add search history and suggestions
- [ ] Implement real-time search results
- [ ] Add search filters and advanced options

**Files to Create/Modify**:
- `frontend/components/search/global-search.tsx`
- `frontend/components/search/search-results.tsx`
- `frontend/hooks/use-global-search.ts`
- `frontend/lib/search-index.ts`

### Task 6.3: Implement Top Bar Component
**Priority**: High
**Estimated Time**: 1 day
**Dependencies**: Task 1.1

**Description**: Create the top navigation bar with search and user controls
- [ ] Implement global search input with proper styling
- [ ] Add user avatar and dropdown menu
- [ ] Include settings and profile navigation
- [ ] Ensure proper backdrop blur and border styling
- [ ] Add keyboard shortcuts (Cmd+K for search)

**Files to Create/Modify**:
- `frontend/components/layout/top-bar.tsx`
- `frontend/hooks/use-keyboard-shortcuts.ts`

### Task 6.4: Implement Assistant Bar Component
**Priority**: High
**Estimated Time**: 1-2 days
**Dependencies**: Task 1.1

**Description**: Create the floating AI assistant input bar
- [ ] Design floating input bar with backdrop blur
- [ ] Add AI command suggestions/quick actions
- [ ] Implement voice input toggle (UI only initially)
- [ ] Add proper form handling and submission
- [ ] Include loading states and feedback

**Files to Create/Modify**:
- `frontend/components/assistant/assistant-bar.tsx`
- `frontend/components/assistant/command-suggestions.tsx`

### Task 6.5: Add Keyboard Shortcuts and Accessibility
**Priority**: Medium
**Estimated Time**: 2-3 days
**Dependencies**: All previous phases

**Description**: Implement comprehensive keyboard navigation
- [ ] Add Cmd+K global search shortcut
- [ ] Implement tool switching shortcuts
- [ ] Add draft pane keyboard shortcuts
- [ ] Include proper ARIA labels and roles
- [ ] Add focus management and navigation
- [ ] Implement screen reader support

**Files to Create/Modify**:
- `frontend/hooks/use-keyboard-shortcuts.ts`
- `frontend/components/accessibility/focus-manager.tsx`
- `frontend/lib/accessibility.ts`

## Phase 7: Performance and Optimization

### Task 7.1: Implement Virtualization and Lazy Loading
**Priority**: Medium
**Estimated Time**: 2-3 days
**Dependencies**: All previous phases

**Description**: Optimize performance for large datasets
- [ ] Add virtual scrolling for email lists
- [ ] Implement lazy loading for documents
- [ ] Add infinite scroll for news feeds
- [ ] Optimize calendar rendering
- [ ] Add proper loading skeletons
- [ ] Implement data caching strategies

**Files to Create/Modify**:
- `frontend/components/ui/virtual-list.tsx`
- `frontend/hooks/use-virtualization.ts`
- `frontend/components/ui/loading-skeleton.tsx`
- `frontend/lib/cache-manager.ts`

### Task 7.2: Add Offline Support and Sync
**Priority**: Low
**Estimated Time**: 3-4 days
**Dependencies**: Task 7.1

**Description**: Implement offline capabilities
- [ ] Add service worker for offline caching
- [ ] Implement offline draft saving
- [ ] Add sync when online
- [ ] Include conflict resolution
- [ ] Add offline indicators
- [ ] Implement background sync

**Files to Create/Modify**:
- `frontend/service-worker.ts`
- `frontend/hooks/use-offline.ts`
- `frontend/lib/sync-manager.ts`
- `frontend/components/ui/offline-indicator.tsx`

## Implementation Notes

### Design System Consistency
- Use existing shadcn/ui components where possible
- Maintain consistent spacing, typography, and color schemes
- Follow the prototype's visual hierarchy and layout patterns

### State Management Strategy
- Use React Context for global state (tool switching, user preferences)
- Use local state for component-specific data
- Consider Zustand for complex state management if needed

### API Integration Approach
- Extend existing API clients in `frontend/lib/`
- Maintain consistent error handling patterns
- Add proper TypeScript types for all API responses

### Testing Strategy
- Add unit tests for utility functions and hooks
- Include integration tests for key user flows
- Add visual regression tests for critical components

### Migration Strategy
- Implement new layout alongside existing dashboard
- Allow gradual migration of existing features
- Maintain backward compatibility during transition

## Success Criteria

1. **Layout**: 3-pane layout matches prototype design
2. **Navigation**: Smooth tool switching with proper state management
3. **Responsiveness**: Works well on desktop and tablet
4. **Performance**: Fast loading and smooth interactions
5. **Accessibility**: Full keyboard navigation and screen reader support
6. **Integration**: Seamless connection with existing backend services
7. **User Experience**: Intuitive and efficient workflow

## Timeline Estimate

- **Phase 0**: 1 week (Integration streamlining)
- **Phase 1-2**: 1-2 weeks (Core layout and navigation)
- **Phase 3**: 3-4 weeks (Core tool views)
- **Phase 4**: 2-3 weeks (Advanced tool views)
- **Phase 5**: 1-2 weeks (Draft pane and AI integration)
- **Phase 6**: 1-2 weeks (Integration and polish)
- **Phase 7**: 1-2 weeks (Performance optimization)

**Total Estimated Time**: 10-16 weeks for full implementation 

## Future ideas:

1. TODOs:  perhaps in the future we'll enable it to be a floating thing or a popdown from the nav bar or split the draft pane, but not now