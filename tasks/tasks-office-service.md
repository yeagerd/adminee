# Office Service Task List

## References
* Design doc: `documentation/office-service.md`
* Backend architecture: `/documentation/backend-architecture.md`

## Task List Management

Guidelines for managing task lists in markdown files to track progress on completing a PRD

### Task Implementation
- **One sub-task at a time:** 
- **Completion protocol:**  
  1. When you finish a **sub‑task**, immediately mark it as completed by changing `[ ]` to `[x]`.  
  2. If **all** subtasks underneath a parent task are now `[x]`, also mark the **parent task** as completed.  

### Task List Maintenance

1. **Update the task list as you work:**
   - Mark tasks and subtasks as completed (`[x]`) per the protocol above.
   - Add new tasks as they emerge.

2. **Maintain the “Relevant Files” section:**
   - List every file created or modified.
   - Give each file a one‑line description of its purpose.

### AI Instructions

When working with task lists, the AI must:

1. Regularly update the task list file after finishing any significant work.
2. Follow the completion protocol:
   - Mark each finished **sub‑task** `[x]`.
   - Mark the **parent task** `[x]` once **all** its subtasks are `[x]`.
3. Add newly discovered tasks.
4. Keep “Relevant Files” accurate and up to date.
5. Before starting work, check which sub‑task is next.
6. After implementing a sub‑task, update this file.

##
General instructions for working in Python in this repo:

Setup:
* Activate the virtual environment: `source venv/bin/activate`
* Run all Python commands from the repository root.

Before committing:
* Run `pytest` and fix all test failures.
* Run `mypy services/` and resolve all type errors.
* Fix lint issues using `./fix`
* Run `tox` to validate the full test matrix and environment compatibility.


## Tasks
[x] 1. Project Scaffolding & Core Dependencies

[x] 1.1 Create a folder for the service in services/office_service.
[x] 1.2 [Install core dependencies: fastapi, uvicorn, pydantic, ormar, alembic, psycopg2-binary, python-dotenv, httpx.]
[x] 1.3 [Set up the basic project structure with folders for app, core, models, tests, etc.]
[x] 1.4 [Create a basic FastAPI application instance in app/main.py with a "Hello World" root endpoint.]
[x] 1.5 [Implement environment variable loading using Pydantic's BaseSettings to manage configuration from the .env file as specified in Section 9.1.]
[x] 1.6 [Define the Ormar models (ApiCall, CacheEntry, RateLimitBucket) in a models/ directory as specified in Section 5.1.]
[x] 1.7 [Configure the database connection using the DATABASE_URL and initialize Alembic for database migrations.]
[x] 1.8 [Generate and apply the initial Alembic migration to create the tables for the models defined in step 1.6.]

[x] 2. Core Module: Pydantic & Error Models
[x] 2.1 [Create a schemas/ directory to hold all Pydantic models for API responses.]
[x] 2.2 [Define the unified Pydantic models for Email (EmailAddress, EmailMessage), Calendar (CalendarEvent, Calendar), and Files (DriveFile) from Section 5.2.]
[x] 2.3 [Define the generic API response models (ApiResponse, PaginatedResponse) from Section 5.2.]
[x] 2.4 [Define the standardized ApiError model from Section 7.1.]

[x] 3. Core Module: Token Manager
[x] 3.1 [Create a core/token_manager.py module.]
[x] 3.2 [Implement the TokenManager class with the async get_user_token method as shown in Section 3.1.]
[x] 3.3 [Integrate an httpx.AsyncClient into the TokenManager to make requests to the USER_MANAGEMENT_SERVICE_URL.]
[x] 3.4 [Add robust error handling and logging for cases where token retrieval fails.]
[x] 3.5 [Implement a simple in-memory cache (e.g., using a dictionary with TTL) within the TokenManager to reduce calls for the same token within a short period (as mentioned in Section 2.1).]

[x] 4. Core Module: API Client Factory
[x] 4.1 [Create a core/clients/ directory for provider-specific clients.]
[x] 4.2 [Implement a base API client class that includes an httpx.AsyncClient and basic request/response logging.]
[x] 4.3 [Create a GoogleAPIClient that inherits from the base client. It should be initialized with a user's access token.]
[x] 4.4 [Create a MicrosoftAPIClient that inherits from the base client, also initialized with a user's access token.]
[x] 4.5 [Implement an APIClientFactory in core/api_client_factory.py that takes a user_id and provider and uses the TokenManager to fetch a token and return an initialized provider-specific API client.]

[x] 5. Core Module: Data Normalizer
[x] 5.1 [Create a core/normalizer.py module.]
[x] 5.2 [Implement a function normalize_google_email that takes a raw JSON response from the Gmail API and converts it into the unified EmailMessage Pydantic model.]
[x] 5.3 [Implement a function normalize_microsoft_email that takes a raw JSON response from the Microsoft Graph API and converts it into the unified EmailMessage Pydantic model.]
[x] 5.4 [Implement initial normalization functions for Google Calendar events and Google Drive files, converting them to CalendarEvent and DriveFile models respectively.]

[x] 6. Core Module: Basic Caching (Redis)
[x] 6.1 [Add the redis-py library to the project dependencies.]
[x] 6.2 [Create a core/cache_manager.py module that establishes a connection to Redis using the REDIS_URL.]
[x] 6.3 [Implement the generate_cache_key utility function as specified in Section 6.2.]
[x] 6.4 [Create simple get_from_cache and set_to_cache functions in the CacheManager that interact with Redis.]
[x] 6.5 [Write unit tests for the generate_cache_key function to ensure it is deterministic.]

[x] 7. Implement Health and Diagnostics Endpoints
[x] 7.1 [Create an api/health.py router.]
[x] 7.2 [Implement the GET /health endpoint as specified in Section 9.2, including checks for the database and Redis connections.]
[x] 7.3 [Implement the GET /health/integrations/{user_id} endpoint. For the MVP, this can simply attempt to fetch a token for both 'google' and 'microsoft' for the given user and report success or failure.]

[x] 8. Implement Unified READ Endpoints (MVP)
[x] 8.1 [Create an api/email.py router.]
[x] 8.2 [Implement GET /email/messages. It should use the APIClientFactory to get clients for each provider, make parallel API calls, use the DataNormalizer to unify the results, and aggregate them.]
[x] 8.3 [Integrate the CacheManager into the GET /email/messages endpoint to cache the final aggregated response.]
[x] 8.4 [Create an api/calendar.py router and implement GET /calendar/events following the same pattern as the email endpoint (fetch, normalize, aggregate, cache).]
[x] 8.5 [Create an api/files.py router and implement GET /files following the same pattern.]
[x] 8.6 [Implement the detail endpoint GET /email/messages/{message_id}. This will require logic to determine the correct provider from the message_id to make the API call.]

[ ] 9. Implement Unified WRITE Endpoints (MVP)
[ ] 9.1 [Implement POST /email/send in the email router. For the MVP, this can be a simple pass-through that determines the provider and makes the API call. The actual queuing can be stubbed or logged for now.]
[ ] 9.2 [Implement POST /calendar/events. This endpoint will need to take unified CalendarEvent data, "de-normalize" it into the provider-specific format, and use the correct API client to create the event.]
[ ] 9.3 [Implement DELETE /calendar/events/{event_id}. This will require logic to find the original provider and use its API to delete the event.]

[ ] 10. Implement Basic Error Handling & Logging
[ ] 10.1 [Configure structured logging for the application (e.g., using the standard logging library with a JSON formatter).]
[ ] 10.2 [Create a global exception handler in app/main.py using the @app.exception_handler decorator.]
[ ] 10.3 [The handler should catch a custom ProviderAPIError, log the full error, and return a standardized 500-level ApiError response to the client.]
[ ] 10.4 [Modify the API clients to catch httpx exceptions and raise the custom ProviderAPIError to be handled by the global handler.]

[ ] 11. Testing and Documentation
[ ] 11.1 [Create a tests/ directory with pytest.]
[ ] 11.2 [Write unit tests for the DataNormalizer functions using the mock data examples from Section 10.3.]
[ ] 11.3 [Write integration tests for the GET /health endpoint.]
[ ] 11.4 [Add docstrings to all public functions and classes you've created.]
[ ] 11.5 [Update the README.md file with instructions on how to set up the development environment, run the service, and run tests.]
## Relevant Files

### Core Infrastructure
- `services/office_service/app/main.py` - FastAPI application with all routers
- `services/office_service/core/config.py` - Environment configuration using Pydantic BaseSettings
- `services/office_service/core/database.py` - Database connection and Ormar configuration
- `services/office_service/alembic/` - Database migration files and configuration

### Data Models
- `services/office_service/models/__init__.py` - Ormar database models (ApiCall, CacheEntry, RateLimitBucket)
- `services/office_service/schemas/__init__.py` - Pydantic schemas for unified API responses (EmailMessage, CalendarEvent, DriveFile, ApiResponse)

### Core Modules
- `services/office_service/core/token_manager.py` - Token retrieval from User Management Service with caching
- `services/office_service/core/api_client_factory.py` - Factory for creating provider-specific API clients
- `services/office_service/core/clients/base.py` - Base API client with logging and error handling
- `services/office_service/core/clients/google.py` - Google API client for Gmail, Calendar, Drive
- `services/office_service/core/clients/microsoft.py` - Microsoft Graph API client for Outlook, Calendar, OneDrive
- `services/office_service/core/normalizer.py` - Data normalization functions for unified response format
- `services/office_service/core/cache_manager.py` - Redis caching with TTL and key generation

### API Endpoints
- `services/office_service/api/health.py` - Health check and diagnostics endpoints
- `services/office_service/api/email.py` - Unified email endpoints (GET /email/messages, GET /email/messages/{id})
- `services/office_service/api/calendar.py` - Unified calendar endpoints (GET /calendar/events, GET /calendar/events/{id})
- `services/office_service/api/files.py` - Unified files endpoints (GET /files/, GET /files/search, GET /files/{id})

### Dependencies
- `requirements.txt` - Python package dependencies including FastAPI, Redis, httpx, Ormar

Next Steps (After MVP)

Once you've completed the tasks above, we'll move on to Phase 2, which includes:

Advanced rate limiting
More sophisticated caching with event-based invalidation
Implementing the remaining endpoints (/contacts, /availability, etc.)
Full implementation of the background task manager.