# Meeting Scheduler Tool - Technical Design Document

## 1. Requirements Specification

### 1.1 Functional Requirements

#### Core Features
- **Meeting Poll Management**: Create, edit, and manage meeting polls with multiple time slot options
- **Multi-Platform Calendar Integration**: Support for Microsoft and Google calendar APIs
- **Recipient Response Collection**: Accept responses via web interface and email parsing
- **Real-time Status Tracking**: Dashboard showing poll status, responses, and analytics

#### Meeting Poll Requirements
- **Time Slot Management**: 
  - Auto-suggest available slots based on organizer's calendar
  - Allow manual addition/removal of time slots
  - Support different time zones for participants
  - Handle business hours preferences
- **Participant Management**:
  - Add/remove participants
  - Track response status (pending, responded, declined)
  - Send reminder notifications
- **Poll Settings**:
  - Set response deadline
  - Require minimum participants for meeting confirmation
  - Allow anonymous vs. named responses
  - Set meeting location (physical, virtual, TBD)

#### Response Collection Requirements
- **Web Interface**:
  - Mobile-responsive poll response page
  - Calendar-style time slot selection
  - Participant availability visualization
  - Optional comment/note field for each response
- **Email Integration**:
  - Parse email replies for time preferences
  - Support various email response formats
  - Handle out-of-office and delegation responses
  - Automatic response confirmation emails

#### Meeting Polls Dashboard Requirements
- **Poll Status Overview**:
  - Active polls (awaiting responses)
  - Completed polls (ready to schedule)
  - Past meetings
  - Draft polls
- **Analytics and Insights**:
  - Response rate tracking
  - Most popular time slots
  - Average response time
- **Bulk Actions**:
  - Send reminders to non-responders
  - Duplicate poll templates
  - Export poll data

### 1.2 Non-Functional Requirements

#### Performance Requirements
- Poll response page load time < 2 seconds
- Support for up to 50 participants per poll
- Handle 1000+ concurrent poll responses
- Real-time updates for poll organizers

#### Security Requirements
- Secure poll URLs (non-guessable tokens)
- Rate limiting for poll responses
- Data privacy compliance (GDPR, CCPA)
- Secure email parsing and processing

#### Usability Requirements
- Mobile-first responsive design for poll responses
- Clear visual indicators for availability conflicts

### 1.3 Integration Requirements
- Microsoft Graph API for Outlook calendar and email
- Google Calendar API and Gmail API
- Existing user authentication system
- Email sending service (SendGrid, AWS SES, etc.)
- Real-time notification system (WebSocket or SSE)

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   External APIs │
│                 │    │                 │    │                 │
│ • AI Chat UI    │◄──►│ • Meeting Poll  │◄──►│ • Google APIs   │
│ • Poll Response │    │   Service       │    │ • Microsoft     │
│ • Dashboard     │    │ • AI Service    │    │   Graph API     │
│ • Calendar View │    │ • Email Service │    │ • Email Service │
└─────────────────┘    │ • Auth Service  │    └─────────────────┘
                       └─────────────────┘
                              │
                       ┌─────────────────┐
                       │    Database     │
                       │                 │
                       │ • Meeting Polls │
                       │ • Participants  │
                       │ • Responses     │
                       │ • User Prefs    │
                       └─────────────────┘
```

### 2.2 Database Schema

#### Meeting Polls Table
```sql
CREATE TABLE meeting_polls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    location VARCHAR(500),
    meeting_type ENUM('in_person', 'virtual', 'tbd') DEFAULT 'tbd',
    status ENUM('draft', 'active', 'closed', 'scheduled') DEFAULT 'draft',
    response_deadline TIMESTAMP WITH TIME ZONE,
    min_participants INTEGER DEFAULT 1,
    max_participants INTEGER,
    allow_anonymous_responses BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    scheduled_slot_id UUID REFERENCES time_slots(id),
    poll_token VARCHAR(64) UNIQUE NOT NULL -- For secure URL access
);
```

#### Time Slots Table
```sql
CREATE TABLE time_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    poll_id UUID NOT NULL REFERENCES meeting_polls(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    timezone VARCHAR(50) NOT NULL,
    is_available BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Poll Participants Table
```sql
CREATE TABLE poll_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    poll_id UUID NOT NULL REFERENCES meeting_polls(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    status ENUM('pending', 'responded', 'declined') DEFAULT 'pending',
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    responded_at TIMESTAMP WITH TIME ZONE,
    reminder_sent_count INTEGER DEFAULT 0,
    UNIQUE(poll_id, email)
);
```

#### Poll Responses Table
```sql
CREATE TABLE poll_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    poll_id UUID NOT NULL REFERENCES meeting_polls(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES poll_participants(id) ON DELETE CASCADE,
    time_slot_id UUID NOT NULL REFERENCES time_slots(id) ON DELETE CASCADE,
    response ENUM('available', 'unavailable', 'maybe') NOT NULL,
    comment TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(participant_id, time_slot_id)
);
```


### 2.3 API Endpoints

#### Meeting Poll Management
```typescript

// CRUD operations for meeting polls
GET /api/meetings/polls
GET /api/meetings/polls/:pollId
POST /api/meetings/polls
PUT /api/meetings/polls/:pollId
DELETE /api/meetings/polls/:pollId

// Time slot management
POST /api/meetings/polls/:pollId/slots
PUT /api/meetings/polls/:pollId/slots/:slotId
DELETE /api/meetings/polls/:pollId/slots/:slotId

// Send poll invitations
POST /api/meetings/polls/:pollId/send-invitations
```

#### Poll Response Collection
```typescript
// Public poll response page (no auth required)
GET /api/public/polls/:token
POST /api/public/polls/:token/respond
{
  participantEmail: string;
  responses: Array<{
    timeSlotId: string;
    response: 'available' | 'unavailable' | 'maybe';
    comment?: string;
  }>;
}

// Email response processing
POST /api/meetings/process-email-response
{
  emailId: string;
  content: string;
  sender: string;
}
```

#### Calendar Integration
```typescript
// Get user availability
GET /api/calendar/availability?start=2024-01-01&end=2024-01-31&duration=60

// Create calendar event after poll closes
POST /api/calendar/create-meeting
{
  pollId: string;
  selectedSlotId: string;
  participants: string[];
}
```

## 3. Implementation Plan

### 3.1 Phase 1: Core Infrastructure (Week 1-2)

#### Backend Setup
1. **Database Schema Implementation**
   - Create all tables with proper indexes
   - Set up database migrations
   - Add foreign key constraints and triggers

2. **Basic API Framework**
   - Set up CRUD endpoints for meeting polls
   - Implement authentication middleware
   - Add input validation and error handling

3. **Calendar Integration Foundation**
   - Extend existing OAuth flow for calendar permissions
   - Create calendar service abstraction layer
   - Implement availability checking logic

#### Frontend Foundation
1. **Meeting Polls Dashboard**
   - Create basic poll listing page
   - Add poll creation form
   - Implement poll editing interface

2. **Public Poll Response Page**
   - Design mobile-responsive layout
   - Create time slot selection interface
   - Add form validation and submission

### 3.3 Phase 3: Email Integration (Week 5-6)

#### Email Response Processing
```typescript
class EmailResponseProcessor {
  async processEmailResponse(emailContent: string, sender: string): Promise<void> {
    // Parse email for poll responses
    // Match sender to poll participant
    // Extract time preferences from email text
    // Update database with responses
    // Send confirmation email
  }

  private parseTimePreferences(emailText: string): ResponseData[] {
    // Handle various email response formats:
    // "I'm available Monday 9am and Tuesday 2pm"
    // "Can't do morning slots, afternoon works"
    // "All times work except Friday"
  }
}
```

#### Email Webhook Integration
1. **Inbound Email Processing**
   - Set up email webhook endpoints
   - Implement email parsing logic
   - Handle edge cases and malformed responses

2. **Email Template System**
   - Create invitation email templates
   - Design reminder email workflows
   - Implement confirmation emails

### 3.4 Phase 4: Advanced Features (Week 7-8)

#### Real-time Updates
1. **WebSocket Implementation**
   - Real-time poll response updates for organizers
   - Live participant count and status
   - Instant notifications for new responses

2. **Smart Scheduling Logic**
   - Automatic meeting confirmation when criteria met
   - Conflict detection and resolution suggestions
   - Optimal time slot recommendations

#### Analytics and Reporting
1. **Poll Analytics Dashboard**
   - Response rate tracking
   - Popular time slot analysis
   - Meeting scheduling success metrics

2. **User Preferences Learning**
   - Track user's preferred meeting times
   - Learn from successful polls
   - Suggest improved time slots

## 4. Technical Considerations

### 4.1 Security Implementation

#### Poll Access Security
```typescript
// Generate secure poll tokens
const generatePollToken = (): string => {
  return crypto.randomBytes(32).toString('hex');
};

// Rate limiting for poll responses
const pollResponseLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 10, // Limit each IP to 10 requests per windowMs
  message: 'Too many poll responses, try again later',
});
```

#### Data Privacy
- Implement data retention policies
- Add GDPR-compliant data deletion
- Encrypt sensitive poll data
- Audit logging for all poll activities

### 4.2 Performance Optimization

#### Database Optimization
```sql
-- Indexes for common queries
CREATE INDEX idx_meeting_polls_user_status ON meeting_polls(user_id, status);
CREATE INDEX idx_poll_participants_poll_status ON poll_participants(poll_id, status);
CREATE INDEX idx_time_slots_poll_time ON time_slots(poll_id, start_time);
CREATE INDEX idx_poll_responses_participant_slot ON poll_responses(participant_id, time_slot_id);
```

#### Caching Strategy
- Cache user calendar availability (5-minute TTL)
- Cache poll response counts and status
- Use Redis for real-time poll updates
- Implement CDN for public poll pages

### 4.3 Error Handling and Resilience

#### Graceful Degradation
- Fallback to email-only responses if web interface fails
- Queue failed calendar API calls for retry
- Handle partial email parsing failures gracefully

#### Monitoring and Alerting
- Track poll creation and response success rates
- Monitor calendar API rate limits and errors
- Alert on email processing failures
- Set up uptime monitoring for public poll URLs

## 5. Testing Strategy

### 5.1 Unit Testing
- Calendar availability logic
- Email response processing
- Poll response validation

### 5.2 Integration Testing
- End-to-end poll creation workflow
- Calendar API integration reliability
- Email sending and processing pipeline
- Real-time update delivery

### 5.3 User Acceptance Testing
- Mobile poll response experience
- Email workflow completeness
- Dashboard functionality and performance

## 6. Deployment and Operations

### 6.1 Infrastructure Requirements
- Horizontal scaling for poll response handling
- Email processing queue (Redis/RabbitMQ)
- File storage for poll data exports
- SSL certificates for public poll domains

### 6.2 Monitoring Dashboard
- Poll creation and completion metrics
- Calendar API usage and quotas
- Email processing success rates
- User engagement analytics

### 6.3 Backup and Recovery
- Automated database backups
- Poll data export functionality
- Calendar event creation retry logic
- Email notification backup systems

This technical design provides a comprehensive foundation for implementing the meeting scheduler tool. The modular approach allows for iterative development while maintaining system scalability and reliability.

## New Feature: Per-Recipient Poll Response Tokens and URLs

### Overview
To enhance poll response security and tracking, each poll recipient will receive a unique, long, random URL specific to them and the meeting. This URL will be used as a special authentication mechanism for submitting poll responses, ensuring that only the intended recipient can respond using their link.

### Implementation Tasks
- [x] **Database Migration:**
  - [x] Add a `response_token` (unique, random string) column to the `poll_participants` table.
  - [x] Ensure this token is unique and not nullable.
- [x] **Model Update:**
  - [x] Update the `PollParticipant` model to include the new `response_token` field.
- [x] **Poll Creation Logic:**
  - [x] When creating poll participants, generate and store a unique `response_token` for each.
- [x] **Invitation Email Update:**
  - [x] Send invitation emails with URLs like `/public/meetings/respond/{response_token}` for each participant.
- [x] **New Public API Endpoint:**
  - [x] Implement `PUT /public/meetings/response/{response_token}` to accept poll responses using only the token.
  - [x] The endpoint should look up the participant by their `response_token`, verify the poll, and accept the response.
- [ ] **Frontend Update:**
  - [ ] Update the public poll response page to support the new URL structure and API.
  - [ ] Remove the legacy meeting id from the frontend, backend, and DB.
- [ ] **Secure Email Processing API**
  - [ ] process_email_response(..) should validate an API key
- [x] **Testing:**
  - [x] Add unit and integration tests for the new token-based response flow.


## Outstanding Implementation Tasks

### Backend
- [x] Implement calendar integration (availability, event creation)
- [x] Add email invitation and response processing
- [ ] Add analytics endpoints and real-time updates (WebSocket/SSE)
- [x] Add public poll response endpoints and security/rate limiting
- [x] Expand tests for all workflows (unit/integration)

### Frontend
- [x] Send out emails upon Meeting Poll Create/Send button.
- [x] Build public poll response page (mobile-friendly)
- [x] Enhance poll creation wizard (multi-step, validation, time zones)
- [x] Add response visualization and analytics to results page
- [ ] Add real-time updates and notifications
- [ ] Improve error/loading/mobile support
- [ ] Add automated frontend tests

### DevOps/Docs
- [ ] Generate/apply Alembic migrations for meetings
- [ ] Add MEETINGS_SERVICE_URL to gateway/.env and docs
- [ ] Expand README/setup documentation for meetings service
