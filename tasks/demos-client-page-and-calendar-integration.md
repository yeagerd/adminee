# Demos Client Page and Calendar Integration Task List

## Overview
This task list outlines the implementation of (a) a `/demos` client page that displays the current dashboard with demo data, and (b) connects the calendar component to real office service data via the gateway.

## Current State Analysis
- Dashboard page exists at `/dashboard` with sample calendar events
- Gateway is configured to route `/api/calendar` requests to office service
- Office service has comprehensive calendar API endpoints
- Frontend uses `gatewayClient` for API communication
- Sample events are hardcoded in `calendar-event-item.tsx`

## Task Breakdown

### Phase 1: Create Demos Client Page

- [x] 1. Create Demos Page Structure
  - [x] 1.1 Create `/frontend/app/demos/page.tsx` with dashboard layout
  - [x] 1.2 Add demos route to Next.js routing configuration
  - [x] 1.3 Create demos-specific layout component that mirrors dashboard layout
  - [x] 1.4 Add navigation link to demos page in navbar component

- [x] 2. Implement Demo Data Management
  - [x] 2.1 Create `/frontend/lib/demo-data.ts` for centralized demo data management
  - [x] 2.2 Extract sample events from `calendar-event-item.tsx` into demo data file
  - [x] 2.3 Create demo user session data for consistent demo experience
  - [x] 2.4 Add demo task list data to complement calendar events

- [x] 3. Create Demo-Specific Components
  - [x] 3.1 Create `DemoScheduleList` component that uses demo data instead of real API calls
  - [x] 3.2 Create `DemoTaskList` component with sample task data
  - [x] 3.3 Create `DemoChatInterface` component that simulates AI responses
  - [x] 3.4 Add demo mode indicators and watermarks to distinguish from real data

- [x] 4. Implement Demo Page Features
  - [x] 4.1 Add demo mode toggle to switch between demo and real data
  - [x] 4.2 Create demo integration status indicators (Google/Microsoft connected)
  - [x] 4.3 Add demo-specific quick actions and buttons
  - [x] 4.4 Implement demo data refresh functionality

### Phase 2: Connect Calendar to Real Office Service Data

- [x] 5. Update Gateway Client for Calendar Integration
  - [x] 5.1 Fix `gatewayClient.getCalendarEvents()` method to match office service API parameters (providers array, limit, start_date, end_date, etc.)
  - [x] 5.2 Add proper TypeScript interfaces for the unified `CalendarEvent` schema from office service
  - [x] 5.3 Add error handling and retry logic for calendar API calls
  - [x] 5.4 Add loading states and error states for calendar data fetching

- [x] 6. Update Schedule List Component
  - [x] 6.1 Modify `ScheduleList` component to fetch real calendar data via gateway using the unified `CalendarEvent` interface
  - [x] 6.2 Add date range filtering (today, this week, custom range) using office service date parameters
  - [x] 6.3 Implement real-time calendar data refresh functionality
  - [x] 6.4 Add loading skeletons and error handling for calendar events

- [x] 7. Update Calendar Event Item Component
  - [x] 7.1 Modify `CalendarEventItem` to work with the unified `CalendarEvent` schema from office service
  - [x] 7.2 Update component props interface to match the office service `CalendarEvent` structure
  - [x] 7.3 Map office service attendee/organizer data to component display format (no timezone conversion needed - office service handles this)
  - [x] 7.4 Implement proper display of provider information (Google/Microsoft) and account details

- [x] 8. Leverage Office Service Data Harmonization
  - [x] 8.1 Update frontend to use the unified `CalendarEvent` schema from office service
  - [x] 8.2 Remove any frontend data transformation logic since office service handles Google/Microsoft format differences
  - [x] 8.3 Update `CalendarEventItem` component to work with the unified `CalendarEvent` interface
  - [x] 8.4 Add proper TypeScript interfaces that match the office service `CalendarEvent` schema

### Phase 3: Integration and Testing

- [x] 9. Dashboard Integration
  - [x] 9.1 Update main dashboard to use real calendar data when integrations are active
  - [x] 9.2 Add integration status checks before making calendar API calls
  - [x] 9.3 Implement graceful fallback to demo data when no integrations are connected
  - [x] 9.4 Add calendar data caching to improve performance

- [x] 10. Error Handling and User Experience
  - [x] 10.1 Add comprehensive error handling for calendar API failures
  - [x] 10.2 Implement user-friendly error messages for calendar connection issues
  - [x] 10.3 Add retry mechanisms for failed calendar data requests
  - [x] 10.4 Create loading states and progress indicators for calendar operations

- [x] 11. Testing and Validation
  - [x] 11.1 Create unit tests for demo data components
  - [x] 11.2 Add integration tests for calendar API calls via gateway
  - [x] 11.3 Test calendar data display and formatting (no transformation needed)
  - [x] 11.4 Validate error handling and edge casesz

### Phase 3.5: Code Quality Improvements

- [x] 11.5 Fix Frontend Code Quality Issues
  - [x] 11.5.1 Fix ESLint warnings in schedule-list.tsx React Hook dependencies
  - [x] 11.5.2 Refactor useMemo dependencies to use proper dependency arrays
  - [x] 11.5.3 Extract complex expressions from dependency arrays to separate variables
  - [x] 11.5.4 Add ESLint configuration to prevent future dependency issues

- [ ] 11.6 Implement Frontend Testing Infrastructure
  - [ ] 11.6.1 Set up Jest and React Testing Library for frontend tests
  - [ ] 11.6.2 Create test configuration for Next.js components
  - [ ] 11.6.3 Add unit tests for CalendarCache class functionality
  - [ ] 11.6.4 Add unit tests for CalendarErrorHandler class
  - [ ] 11.6.5 Add integration tests for ScheduleList component with mock API
  - [ ] 11.6.6 Add tests for demo data conversion utilities
  - [ ] 11.6.7 Add tests for authentication flow and sign-in page

- [x] 11.7 Optimize Calendar Cache Performance
  - [x] 11.7.1 Add cache size limits to prevent memory leaks
  - [x] 11.7.2 Implement LRU (Least Recently Used) eviction policy
  - [x] 11.7.3 Add cache performance monitoring and metrics
  - [ ] 11.7.4 Implement cache warming for frequently accessed data
  - [ ] 11.7.5 Add cache hit/miss ratio tracking
  - [ ] 11.7.6 Implement cache compression for large event lists

- [x] 11.8 Enhance Error Handling and Edge Cases
  - [x] 11.8.1 Add timezone validation for token expiration timestamps
  - [ ] 11.8.2 Implement retry logic with exponential backoff for network errors
  - [ ] 11.8.3 Add circuit breaker pattern for API calls
  - [ ] 11.8.4 Handle malformed timestamp data gracefully
  - [x] 11.8.5 Add validation for cache key generation to prevent collisions
  - [ ] 11.8.6 Implement proper error boundaries for React components

- [ ] 11.9 Security and Authentication Improvements
  - [ ] 11.9.1 Review and validate JWT token security changes
  - [ ] 11.9.2 Add audience validation back if security requires it
  - [ ] 11.9.3 Implement proper token refresh error handling
  - [ ] 11.9.4 Add security headers and CSRF protection
  - [ ] 11.9.5 Implement proper session management and cleanup
  - [ ] 11.9.6 Add rate limiting for API calls

- [ ] 11.10 Database and Session Management
  - [ ] 11.10.1 Add proper session context managers for database operations
  - [ ] 11.10.2 Implement connection pooling for database sessions
  - [ ] 11.10.3 Add session timeout and cleanup mechanisms
  - [ ] 11.10.4 Implement proper transaction rollback on errors
  - [ ] 11.10.5 Add database connection health checks
  - [ ] 11.10.6 Implement proper session isolation for concurrent requests

- [ ] 11.11 Demo Data and Configuration Improvements
  - [ ] 11.11.1 Make provider configurable in demo data conversion
  - [ ] 11.11.2 Add demo data validation and schema checking
  - [ ] 11.11.3 Implement demo data versioning for backward compatibility
  - [ ] 11.11.4 Add demo data customization options
  - [ ] 11.11.5 Create demo data migration utilities

- [ ] 11.12 Monitoring and Observability
  - [ ] 11.12.1 Add integration health metrics and monitoring
  - [ ] 11.12.2 Implement cache performance analytics
  - [ ] 11.12.3 Add error tracking and alerting for calendar API failures
  - [ ] 11.12.4 Create dashboard for integration status monitoring
  - [ ] 11.12.5 Add user experience metrics tracking
  - [ ] 11.12.6 Implement logging for debugging and troubleshooting

### Phase 4: Advanced Features

- [ ] 12. Calendar Event Management
  - [ ] 12.1 Add "Create Event" functionality that calls office service API
  - [ ] 12.2 Implement event editing capabilities for user-owned events
  - [ ] 12.3 Add event deletion with proper confirmation dialogs
  - [ ] 12.4 Implement event search and filtering capabilities

- [ ] 13. Real-time Updates
  - [ ] 13.1 Implement WebSocket connection for real-time calendar updates
  - [ ] 13.2 Add calendar event notifications and alerts
  - [ ] 13.3 Implement automatic calendar data refresh on user actions
  - [ ] 13.4 Add calendar sync status indicators

- [ ] 14. Performance Optimization
  - [ ] 14.1 Implement calendar data pagination for large event lists
  - [ ] 14.2 Add intelligent caching strategies for calendar data
  - [ ] 14.3 Optimize calendar API calls to reduce bandwidth usage
  - [ ] 14.4 Implement lazy loading for calendar event details

### Phase 4.5: JWT Security Improvements

- [ ] 15. Implement JWT Audience Validation Across All Services
  - [ ] 15.1 Backend User Service JWT Configuration **[HIGH PRIORITY]**
    - [ ] 15.1.1 Add environment variable for JWT audience configuration
    - [ ] 15.1.2 Update settings.py to include NEXTAUTH_AUDIENCE with default value
    - [ ] 15.1.3 Modify nextauth.py to enforce audience validation when configured
    - [ ] 15.1.4 Add audience validation tests in test_auth.py
    - [ ] 15.1.5 Update JWT verification logic to handle multiple audience values
    - [ ] 15.1.6 Add configuration validation for audience settings

  - [ ] 15.2 Frontend NextAuth Configuration **[HIGH PRIORITY]**
    - [ ] 15.2.1 Update frontend/lib/auth.ts to include audience in JWT generation
    - [ ] 15.2.2 Add environment variable for frontend JWT audience
    - [ ] 15.2.3 Configure NextAuth.js to include audience claim in tokens
    - [ ] 15.2.4 Update JWT signing configuration in auth options
    - [ ] 15.2.5 Add audience validation in frontend token verification
    - [ ] 15.2.6 Test JWT generation with audience claims

  - [ ] 15.3 Chat Service JWT Integration **[MEDIUM PRIORITY]**
    - [ ] 15.3.1 Update chat service to validate JWT audience
    - [ ] 15.3.2 Add JWT audience configuration to chat service settings
    - [ ] 15.3.3 Modify chat service authentication middleware
    - [ ] 15.3.4 Add audience validation tests for chat service
    - [ ] 15.3.5 Update chat service to handle multiple audience values

  - [ ] 15.4 Office Service JWT Integration **[MEDIUM PRIORITY]**
    - [ ] 15.4.1 Update office service to validate JWT audience
    - [ ] 15.4.2 Add JWT audience configuration to office service settings
    - [ ] 15.4.3 Modify office service authentication middleware
    - [ ] 15.4.4 Add audience validation tests for office service
    - [ ] 15.4.5 Update office service to handle multiple audience values

  - [ ] 15.5 Demo Environment JWT Configuration **[MEDIUM PRIORITY]**
    - [ ] 15.5.1 Update services/demos/nextauth_demo_utils.py to use proper audience
    - [ ] 15.5.2 Modify create_nextauth_jwt_for_demo function to include audience
    - [ ] 15.5.3 Update demo JWT generation to match production configuration
    - [ ] 15.5.4 Add audience validation in demo authentication flows
    - [ ] 15.5.5 Update demo tests to include audience validation
    - [ ] 15.5.6 Configure demo environment variables for JWT audience

  - [ ] 15.6 Gateway JWT Validation **[LOW PRIORITY]**
    - [ ] 15.6.1 Update gateway to validate JWT audience before forwarding
    - [ ] 15.6.2 Add JWT audience configuration to gateway settings
    - [ ] 15.6.3 Modify gateway authentication middleware
    - [ ] 15.6.4 Add audience validation tests for gateway
    - [ ] 15.6.5 Update gateway to handle multiple audience values

  - [ ] 15.7 Environment Configuration Management **[MEDIUM PRIORITY]**
    - [ ] 15.7.1 Create centralized JWT configuration documentation
    - [ ] 15.7.2 Add environment variable templates for all services
    - [ ] 15.7.3 Create configuration validation scripts
    - [ ] 15.7.4 Add JWT audience configuration to deployment scripts
    - [ ] 15.7.5 Update Docker configurations with JWT environment variables
    - [ ] 15.7.6 Create configuration migration guide for existing deployments

  - [ ] 15.8 Security Testing and Validation **[HIGH PRIORITY]**
    - [ ] 15.8.1 Add comprehensive JWT audience validation tests
    - [ ] 15.8.2 Test JWT token rejection with invalid audience
    - [ ] 15.8.3 Test JWT token acceptance with valid audience
    - [ ] 15.8.4 Add integration tests for cross-service JWT validation
    - [ ] 15.8.5 Test JWT audience validation in demo environment
    - [ ] 15.8.6 Add security audit tests for JWT configuration

  - [ ] 15.9 Documentation and Migration **[LOW PRIORITY]**
    - [ ] 15.9.1 Update API documentation with JWT audience requirements
    - [ ] 15.9.2 Create JWT configuration migration guide
    - [ ] 15.9.3 Add troubleshooting guide for JWT audience issues
    - [ ] 15.9.4 Update deployment documentation with JWT configuration
    - [ ] 15.9.5 Create security best practices documentation
    - [ ] 15.9.6 Add monitoring and alerting for JWT validation failures

## Implementation Notes

### File Structure Changes
```
frontend/
├── app/
│   └── demos/
│       └── page.tsx (new)
├── components/
│   ├── demo-schedule-list.tsx (new)
│   ├── demo-task-list.tsx (new)
│   ├── demo-chat-interface.tsx (new)
│   ├── schedule-list.tsx (modified)
│   └── calendar-event-item.tsx (modified)
├── lib/
│   ├── demo-data.ts (new)
│   └── gateway-client.ts (modified)
└── types/
    └── office-service.ts (new - unified interfaces from office service)
```

### API Integration Points
- Gateway routes `/api/calendar/*` to office service
- Office service provides `/calendar/events` endpoint
- Frontend uses `gatewayClient.getCalendarEvents()` method
- Authentication handled via JWT tokens in gateway

### Data Flow
1. User visits `/demos` → Shows dashboard with demo data
2. User toggles to real mode → Fetches calendar data via gateway
3. Gateway authenticates and routes to office service
4. Office service normalizes Google/Microsoft data and returns unified `CalendarEvent` objects
5. Frontend displays the unified calendar data directly (no transformation needed)

### Key Considerations
- Maintain backward compatibility with existing demo data
- Handle authentication and authorization properly
- Implement proper error handling for API failures
- Office service already handles timezone differences and provider format normalization
- Ensure responsive design for mobile devices
- Add proper loading states and user feedback
- Leverage existing office service data harmonization instead of creating duplicate logic

## Success Criteria
- [ ] Demos page displays current dashboard layout with demo data
- [ ] Calendar component successfully fetches and displays real calendar events
- [ ] Seamless transition between demo and real data modes
- [ ] Proper error handling for API failures
- [ ] Responsive design works on all device sizes
- [ ] All tests pass and code quality standards are met 