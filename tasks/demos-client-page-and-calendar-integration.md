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

- [ ] 1. Create Demos Page Structure
  - [ ] 1.1 Create `/frontend/app/demos/page.tsx` with dashboard layout
  - [ ] 1.2 Add demos route to Next.js routing configuration
  - [ ] 1.3 Create demos-specific layout component that mirrors dashboard layout
  - [ ] 1.4 Add navigation link to demos page in navbar component

- [ ] 2. Implement Demo Data Management
  - [ ] 2.1 Create `/frontend/lib/demo-data.ts` for centralized demo data management
  - [ ] 2.2 Extract sample events from `calendar-event-item.tsx` into demo data file
  - [ ] 2.3 Create demo user session data for consistent demo experience
  - [ ] 2.4 Add demo task list data to complement calendar events

- [ ] 3. Create Demo-Specific Components
  - [ ] 3.1 Create `DemoScheduleList` component that uses demo data instead of real API calls
  - [ ] 3.2 Create `DemoTaskList` component with sample task data
  - [ ] 3.3 Create `DemoChatInterface` component that simulates AI responses
  - [ ] 3.4 Add demo mode indicators and watermarks to distinguish from real data

- [ ] 4. Implement Demo Page Features
  - [ ] 4.1 Add demo mode toggle to switch between demo and real data
  - [ ] 4.2 Create demo integration status indicators (Google/Microsoft connected)
  - [ ] 4.3 Add demo-specific quick actions and buttons
  - [ ] 4.4 Implement demo data refresh functionality

### Phase 2: Connect Calendar to Real Office Service Data

- [ ] 5. Update Gateway Client for Calendar Integration
  - [ ] 5.1 Enhance `gatewayClient.getCalendarEvents()` method to handle date ranges
  - [ ] 5.2 Add error handling and retry logic for calendar API calls
  - [ ] 5.3 Implement proper TypeScript interfaces for calendar event responses
  - [ ] 5.4 Add loading states and error states for calendar data fetching

- [ ] 6. Update Schedule List Component
  - [ ] 6.1 Modify `ScheduleList` component to fetch real calendar data via gateway
  - [ ] 6.2 Add date range filtering (today, this week, custom range)
  - [ ] 6.3 Implement real-time calendar data refresh functionality
  - [ ] 6.4 Add loading skeletons and error handling for calendar events

- [ ] 7. Update Calendar Event Item Component
  - [ ] 7.1 Modify `CalendarEventItem` to handle real calendar event data structure
  - [ ] 7.2 Update event item interface to match office service API response format
  - [ ] 7.3 Add proper date/time formatting for different timezones
  - [ ] 7.4 Implement real attendee status and organizer information display

- [ ] 8. Implement Calendar Data Transformation
  - [ ] 8.1 Create data transformation layer to convert office service format to frontend format
  - [ ] 8.2 Handle different calendar providers (Google, Microsoft) data formats
  - [ ] 8.3 Implement proper timezone handling for calendar events
  - [ ] 8.4 Add fallback handling for missing or malformed calendar data

### Phase 3: Integration and Testing

- [ ] 9. Dashboard Integration
  - [ ] 9.1 Update main dashboard to use real calendar data when integrations are active
  - [ ] 9.2 Add integration status checks before making calendar API calls
  - [ ] 9.3 Implement graceful fallback to demo data when no integrations are connected
  - [ ] 9.4 Add calendar data caching to improve performance

- [ ] 10. Error Handling and User Experience
  - [ ] 10.1 Add comprehensive error handling for calendar API failures
  - [ ] 10.2 Implement user-friendly error messages for calendar connection issues
  - [ ] 10.3 Add retry mechanisms for failed calendar data requests
  - [ ] 10.4 Create loading states and progress indicators for calendar operations

- [ ] 11. Testing and Validation
  - [ ] 11.1 Create unit tests for demo data components
  - [ ] 11.2 Add integration tests for calendar API calls via gateway
  - [ ] 11.3 Test calendar data transformation and formatting
  - [ ] 11.4 Validate error handling and edge cases

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
│   └── schedule-list.tsx (modified)
├── lib/
│   ├── demo-data.ts (new)
│   └── gateway-client.ts (modified)
└── types/
    └── calendar.ts (new)
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
4. Office service returns unified calendar events
5. Frontend transforms and displays real calendar data

### Key Considerations
- Maintain backward compatibility with existing demo data
- Handle authentication and authorization properly
- Implement proper error handling for API failures
- Consider timezone differences in calendar data
- Ensure responsive design for mobile devices
- Add proper loading states and user feedback

## Success Criteria
- [ ] Demos page displays current dashboard layout with demo data
- [ ] Calendar component successfully fetches and displays real calendar events
- [ ] Seamless transition between demo and real data modes
- [ ] Proper error handling for API failures
- [ ] Responsive design works on all device sizes
- [ ] All tests pass and code quality standards are met 