## Relevant Files

### Frontend (Next.js)
- `app/api/auth/[...nextauth]/route.ts` - Microsoft OAuth2 authentication implementation // This will be handled by Clerk; NextAuth route might not be needed or will serve a different purpose.
- `app/page.tsx` - Main dashboard page
- `app/layout.tsx` - Application layout including authentication state
- `app/components/Calendar/CalendarView.tsx` - Interactive calendar component for web app
- `app/components/Tasks/TaskManager.tsx` - Task management component for meeting preparation
- `app/subscription/page.tsx` - Subscription management page
- `app/api/proxy/[...service].ts` - API proxy routes to backend services

### Backend Services
- `services/calendar-service/` - Python FastAPI service for calendar analysis
  - `main.py` - FastAPI application entry point
  - `models.py` - Pydantic models for API
  - `services/calendar_analyzer.py` - Calendar analysis logic
  - `services/rag_pipeline.py` - RAG implementation for meeting context
- `services/email-service/` - Node.js service for email generation and delivery
  - `index.js` - Service entry point
  - `templates/` - Email templates
  - `generators/` - Email content generators
- `services/auth-service/` - Authentication service with Microsoft Graph integration
  - `index.js` - Service entry point
  - `microsoft-graph.js` - Microsoft Graph API client

### Database
- `services/db/migrations/` - PostgreSQL database migrations
- `services/db/models/` - Database models
  - `User.js` - User data model
  - `CalendarEvent.js` - Calendar event data model
  - `Task.js` - Task data model
- `services/db/schema.prisma` - Prisma schema for PostgreSQL


### Vector Database
- `services/vector-db/` - Vector database management
  - `embeddings.py` - Embedding generation utilities
  - `pinecone_client.py` - Pinecone vector DB client
  - `indexing_service.py` - Document indexing service

### Infrastructure
- `docker-compose.yml` - Local development environment
- `Dockerfile.calendar-service` - Dockerfile for calendar analysis service
- `Dockerfile.email-service` - Dockerfile for email service
- `package.json` - Project dependencies for Node.js services
- `requirements.txt` - Python dependencies
- `.env.example` - Example environment variables

### Notes

- Each service has its own test directory (e.g., `services/calendar-service/tests/`)
- Clerk is used for user auth and management
- PostgreSQL is used for structured data storage
- Pinecone vector database is used for RAG embeddings
- LangChain and Sentence-Transformers are used for the RAG pipeline


### Data models
- Users: something like this that provides Firebase-like flexibility, but with SQL robustness:
  CREATE TABLE customer_profiles (
  id UUID PRIMARY KEY,
  user_id TEXT UNIQUE,
  created_at TIMESTAMPTZ,
  profile_data JSONB
);

### Anticipated Auth Scopes
- Microsoft Graph: Calendars.Read, Calendars.ReadWrite, Mail.Read, User.Read, People.Read

## Tasks

- [x] 1. Define System Architecture // Re-marking as complete
  - [x] 1.1 Design database schema for PostgreSQL
  - [x] 1.2 Set up Pinecone vector database
  - [x] 1.3 Set up a dev container
  - [x] 1.4 Create Docker Compose setup for local development
  - [x] 1.5 Design service communication architecture
  - [x] 1.6 Set up deployment environment configuration
  - [x] 1.7 Update `README.md` with build, local testing, unit testing, and deployment instructions
  - [x] 1.8 Document strategy for using a cloud-hosted PostgreSQL provider (e.g., Neon) in production
  - [x] 1.9 Refactor for Multi-Provider Support and User Settings
    - [x] 1.9.1 Update `services/db/schema.prisma` to include `calendarProvider` and `userSettings` in the `User` model.
    - [x] 1.9.2 Create `services/calendar-service/providers/base.py` with `CalendarProvider` abstract base class.
    - [x] 1.9.3 Refactor Microsoft Graph logic from `services/calendar-service/services/graph_client.py` into `services/calendar-service/providers/microsoft_graph.py`, implementing `CalendarProvider`.
    - [x] 1.9.4 Create placeholder `services/calendar-service/providers/google_calendar.py`.
    - [x] 1.9.5 Update `services/calendar-service/main.py` (`/events` endpoint) to accept `provider_type` and use the provider pattern. Default `start/end_datetime` to today if not provided before calling provider.
    - [x] 1.9.6 Delete `services/calendar-service/services/graph_client.py` after refactoring.
    - [x] 1.9.7 Update `services/auth-service/index.js` to expose API endpoints for managing `calendarProvider` and `userSettings` (timezone, email preferences) in the User model.

- [x] 2. Implement Authentication and Microsoft Graph API Integration
  - [x] 2.1 Set up Clerk for auth / accounts using the instructions in `tasks/clerk-install.md`
  - [x] 2.2 Configure Microsoft OAuth (as a social connection) in Clerk and request necessary Graph API scopes
  - [x] 2.3 Implement token management for Microsoft Graph API (retrieving tokens via Clerk)
  - [x] 2.4 Create API client for Microsoft Graph interactions
  - [x] 2.5 Implement user profile and settings storage
  - [x] 2.6 Set up security measures for token storage
  - [x] 2.7 Create user onboarding flow authorizing Microsoft Graph scopes (see above)

- [x] 3. Develop Calendar Analysis Service // Ensuring this is NOT [x]
  - [x] 3.1 Set up FastAPI application structure
  - [x] 3.2 Implement calendar event retrieval from Microsoft Graph // This is now complete due to 1.9
  - [x] 3.3 Create logic for conflict detection
  - [ ] 3.4 Implement attendance analysis
  - [ ] 3.5 Develop work hours conflict detection
  - [ ] 3.6 Create API endpoints for calendar analysis

- [ ] 4.0 Implement RAG Pipeline for Meeting Context
  - [ ] 4.1 Define `VectorStore` abstract base class/interface
  - [ ] 4.2 Implement Pinecone `VectorStore` subclass for production
  - [ ] 4.3 Implement ChromaDB `VectorStore` subclass for local testing/development
  - [ ] 4.4 Set up LangChain environment (was 4.1)
  - [ ] 4.5 Create document retrieval from emails and files (was 4.2)
  - [ ] 4.6 Implement text chunking and processing (was 4.3)
  - [ ] 4.7 Develop embedding generation using Sentence-Transformers (was 4.4)
  - [ ] 4.8 Set up vector storage in Pinecone (was 4.5) // This might be partly covered by 4.2
  - [ ] 4.9 Implement relevance matching for calendar events (was 4.6)
  - [ ] 4.10 Create API for querying relevant meeting context (was 4.7)

- [ ] 5.0 Develop Email Notification System
  - [ ] 5.1 Design email templates for daily summaries
  - [ ] 5.2 Create email templates for alerts
  - [ ] 5.3 Implement email generation service
  - [ ] 5.4 Set up scheduled email delivery for morning summaries
  - [ ] 5.5 Create triggered email alerts for detected scenarios
  - [ ] 5.6 Implement email tracking and analytics

- [ ] 6. Create Web Application User Interface
  - [ ] 6.1 Develop main dashboard layout
  - [ ] 6.2 Create interactive calendar component
  - [ ] 6.3 Implement meeting detail view
  - [ ] 6.4 Design and implement settings page
  - [ ] 6.5 Create user onboarding experience
  - [ ] 6.6 Implement responsive design for mobile compatibility

- [ ] 7. Implement Task Management for Meeting Preparation
  - [ ] 7.1 Create task data model and storage
  - [ ] 7.2 Develop task creation from meeting context
  - [ ] 7.3 Implement task UI components
  - [ ] 7.4 Create task completion tracking
  - [ ] 7.5 Implement task prioritization algorithm
  - [ ] 7.6 Develop meeting preparation recommendations

- [ ] 8. Design and Implement Subscription System
  - [ ] 8.1 Set up Stripe integration for payments
  - [ ] 8.2 Implement subscription tiers and features
  - [ ] 8.3 Create subscription management UI
  - [ ] 8.4 Develop free trial functionality
  - [ ] 8.5 Implement usage tracking for tier limits
  - [ ] 8.6 Set up subscription analytics

- [ ] 9. Testing and Quality Assurance
  - [ ] 9.1 Create unit tests for all services
  - [ ] 9.2 Implement integration tests
  - [ ] 9.3 Set up end-to-end testing
  - [ ] 9.4 Conduct security and privacy review
  - [ ] 9.5 Perform load testing and optimization
  - [ ] 9.6 Create monitoring and alerting system 