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
- `services/office-service/` - Python FastAPI service for calendar analysis
- `services/chat-service/` - Node.js service for email generation and delivery
- `services/auth-service/` - Authentication service with Microsoft Graph integration

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
- `Dockerfile.office-service` - Dockerfile for calendar analysis service
- `Dockerfile.chat-service` - Dockerfile for chat service
- `Dockerfile.user-service` - Dockerfile for user service
- `package.json` - Project dependencies for Node.js services
- `requirements.txt` - Python dependencies
- `.env.example` - Example environment variables

### Notes

- Each service has its own test directory (e.g., `services/office-service/tests/`)
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
  - [x] 3.4 Implement attendance analysis // Un-marking due to revised understanding -> Now complete with new logic
  - [x] 3.5 Develop work hours conflict detection
  - [x] 3.6 Create API endpoints for calendar analysis

- [x] 4.0 Create Web Application User Interface for MVP Demo
  - [x] 4.1 Ensure frontend stack (Next.js, shad-cn, Tailwind CSS) is set up and ready.
    - [x] 4.1.1 Initialize shadcn/ui and configure Tailwind CSS
  - [x] 4.2 Define mock data structures for calendar events and tasks.
  - [x] 4.3 Implement a mock data service/utility within the frontend to provide sample data.
  - [x] 4.4 Design the top-level frontend architecture, navigation flow (login -> onboarding -> dashboard -> settings). // Revisit: Middleware not fully functional
  - [x] 4.4.1 Fix `frontend/src/middleware.ts` to correctly handle authentication, protect routes, and redirect to `/dashboard` or `/onboarding` as per design. Investigate and resolve Clerk auth() typing issues.
  - [ ] 4.5 Design and implement the main "Today" dashboard layout, incorporating:
    - [ ] 4.5.1 Include the Placeholder/Mock-driven interactive calendar view (showing today's schedule).
    - [ ] 4.5.2 Include the Placeholder/Mock-driven task list component (allowing basic CRUD operations on mock tasks).
    - [ ] 4.5.3 Include the chat bar to talk to an LLM model of your choosing, similar to ChatGPT, Claude, or Gemini's homepages. For now, we're just building the FE, but for context, assume that we'll be making calls through our backend so we can add the system prompt, context, authorize the LLM calls, enable tools, take actions, etc.
  - [ ] 4.6 Design and implement a basic settings page (e.g., for timezone, mock data toggles if applicable).  Consider also showing the timezone selector in the navigation pane so it's easy to modify for people who travel.
  - [ ] 4.7 Create a streamlined user onboarding flow (focused on MVP essentials).
  - [ ] 4.8 Basic mobile responsiveness for the MVP views.

- [ ] 5.0 Implement RAG Pipeline for Meeting Context
  - [ ] 5.1 Define `VectorStore` abstract base class/interface
  - [ ] 5.2 Implement Pinecone `VectorStore` subclass for production
  - [ ] 5.3 Implement ChromaDB `VectorStore` subclass for local testing/development
  - [ ] 5.4 Set up LangChain environment
  - [ ] 5.5 Create document retrieval from emails and files
  - [ ] 5.6 Implement text chunking and processing
  - [ ] 5.7 Develop embedding generation using Sentence-Transformers
  - [ ] 5.8 Set up vector storage in Pinecone
  - [ ] 5.9 Implement relevance matching for calendar events
  - [ ] 5.10 Create API for querying relevant meeting context

- [ ] 6.0 Develop Email Notification System
  - [ ] 6.1 Design email templates for daily summaries
  - [ ] 6.2 Create email templates for alerts
  - [ ] 6.3 Implement email generation service
  - [ ] 6.4 Set up scheduled email delivery for morning summaries
  - [ ] 6.5 Create triggered email alerts for detected scenarios
  - [ ] 6.6 Implement email tracking and analytics

- [ ] 7.0 Implement Task Management for Meeting Preparation
  - [ ] 7.1 Create task data model and storage
  - [ ] 7.2 Develop task creation from meeting context
  - [ ] 7.3 Implement task UI components
  - [ ] 7.4 Create task completion tracking
  - [ ] 7.5 Implement task prioritization algorithm
  - [ ] 7.6 Develop meeting preparation recommendations

- [ ] 8.0 Design and Implement Subscription System
  - [ ] 8.1 Set up Stripe integration for payments
  - [ ] 8.2 Implement subscription tiers and features
  - [ ] 8.3 Create subscription management UI
  - [ ] 8.4 Develop free trial functionality
  - [ ] 8.5 Implement usage tracking for tier limits
  - [ ] 8.6 Set up subscription analytics

- [ ] 9.0 Testing and Quality Assurance
  - [ ] 9.1 Create unit tests for all services
  - [ ] 9.2 Implement integration tests
  - [ ] 9.3 Set up end-to-end testing
  - [ ] 9.4 Conduct security and privacy review
  - [ ] 9.5 Perform load testing and optimization
  - [ ] 9.6 Create monitoring and alerting system 