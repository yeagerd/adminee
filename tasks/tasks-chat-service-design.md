## Relevant Files

- `services/chat-service/main.py` - Main entrypoint for the chat-service API (FastAPI or Flask app).
- `services/chat-service/history_manager.py` - Manages thread and message history in the database.
- `services/chat-service/context_module.py` - Implements context condensation and context selection logic.
- `services/chat-service/llm_tools.py` - Custom LiteLLM tools for office-service integration.
- `services/chat-service/llm_usage.py` - Tracks and records LLM usage per invocation.
- `services/chat-service/feedback.py` - Handles feedback API and storage.
- `services/chat-service/models.py` - SQLAlchemy or Pydantic models for threads, messages, feedback, and usage.
- `services/chat-service/tests/test_main.py` - API endpoint tests.
- `services/chat-service/tests/test_history_manager.py` - Unit tests for history manager.
- `services/chat-service/tests/test_context_module.py` - Unit tests for context module.
- `services/chat-service/tests/test_llm_tools.py` - Unit tests for LiteLLM tool integration.
- `services/chat-service/tests/test_llm_usage.py` - Unit tests for LLM usage tracking.
- `services/chat-service/tests/test_feedback.py` - Unit tests for feedback API.
- `services/chat-service/tests/test_models.py` - Unit tests for data models.
- `services/chat-service/Dockerfile` - Containerization for deployment.
- `services/chat-service/requirements.txt` - Python dependencies for the service.
- `services/chat-service/.env.example` - Example environment variables (e.g., LLM provider, DB connection).

### Notes

- Use [Ormar](https://collerek.github.io/ormar/) as the ORM for all database models and operations.
- Use [Alembic](https://alembic.sqlalchemy.org/) for schema migrations and management.
- Unit tests should typically be placed alongside the code files they are testing (e.g., `main.py` and `test_main.py` in the same directory).
- Use `pytest` or `tox` to run tests. Running without a path executes all tests found by the test runner configuration.

## Tasks

- [x] 1. Set up chat-service project structure and dependencies
  - [x] 1.1 Create the `services/chat-service/` directory and initial files.
  - [x] 1.2 Pip install FastAPI/Flask, LiteLLM, SQLAlchemy, and other dependencies.
  - [x] 1.3 Add needed API keys to `.env.example`
  - [x] 1.4 Add `Dockerfile` for containerization.
  - [x] 1.5 Add `requirements.txt` for dependencies.
  - [x] 1.6 Add `.env.example` for environment variables.

- [x] 2. Implement API endpoints for chat, thread management, and feedback
  - [x] 2.1 Implement `/chat` POST endpoint for chat interaction.
  - [x] 2.2 Implement `/threads` GET endpoint to list threads for a user.
  - [x] 2.3 Implement `/threads/{thread_id}/history` GET endpoint for thread history.
  - [x] 2.4 Implement `/feedback` POST endpoint for thumbs up/down feedback.
  - [x] 2.5 Add request validation and response schemas using Pydantic.

- [ ] 3. Implement LiteLLM integration
  - [x] 3.1 Implement calendar tool
    - [x] 3.1.1 Define a LiteLLM tool for retrieving calendar events from office-service via REST API.
    - [x] 3.1.2 Support parameters: user token, date range, user timezone, provider type.
    - [x] 3.1.3 Handle authentication by forwarding the user token.
    - [x] 3.1.4 Parse and validate office-service API responses; handle errors and timeouts.
    - [x] 3.1.5 Return results in a format suitable for LLM context and tool command schema.
    - [x] 3.1.6 Add unit tests for calendar tool, including error cases and edge cases.
  - [x] 3.2 Implement email tool
    - [x] 3.2.1 Define a LiteLLM tool for retrieving emails from office-service via REST API.
    - [x] 3.2.2 Support parameters: user token, date range, filters (e.g., unread, folder).
    - [x] 3.2.3 Forward user token for authentication.
    - [x] 3.2.4 Parse and validate office-service API responses; handle errors and timeouts.
    - [x] 3.2.5 Return results in a format suitable for LLM context and tool command schema.
    - [x] 3.2.6 Add unit tests for email tool, including error and edge cases.
  - [x] 3.3 Implement notes tool
    - [x] 3.3.1 Define a LiteLLM tool for retrieving notes from office-service via REST API.
    - [x] 3.3.2 Support parameters: user token, filters (e.g., notebook, tags).
    - [x] 3.3.3 Forward user token for authentication.
    - [x] 3.3.4 Parse and validate office-service API responses; handle errors and timeouts.
    - [x] 3.3.5 Return results in a format suitable for LLM context and tool command schema.
    - [x] 3.3.6 Add unit tests for notes tool, including error and edge cases.
  - [x] 3.4 Implement documents tool
    - [x] 3.4.1 Define a LiteLLM tool for retrieving documents from office-service via REST API.
    - [x] 3.4.2 Support parameters: user token, filters (e.g., document type, date).
    - [x] 3.4.3 Forward user token for authentication.
    - [x] 3.4.4 Parse and validate office-service API responses; handle errors and timeouts.
    - [x] 3.4.5 Return results in a format suitable for LLM context and tool command schema.
    - [x] 3.4.6 Add unit tests for documents tool, including error and edge cases.
  - [ ] 3.5 Implement create draft email tool
    - [ ] 3.5.1 Define a LiteLLM tool for creating or updating the active draft email for a thread (no office-service call).
    - [ ] 3.5.2 Support parameters: thread id, email content (to, subject, body, etc.).
    - [ ] 3.5.3 Store the draft in the history manager or a dedicated draft store, ensuring only one active draft per thread.
    - [ ] 3.5.4 On chat response, return the current active draft (if any) in the response payload.
    - [ ] 3.5.5 Add unit tests for create draft email tool, including edge cases (e.g., draft already exists, update draft).
  - [ ] 3.6 Implement delete draft email tool
    - [ ] 3.6.1 Define a LiteLLM tool for deleting the active draft email for a thread (no office-service call).
    - [ ] 3.6.2 Support parameters: thread id.
    - [ ] 3.6.3 Remove the draft from the history manager or draft store.
    - [ ] 3.6.4 On chat response, ensure the draft is no longer present in the response payload.
    - [ ] 3.6.5 Add unit tests for delete draft email tool, including edge cases (e.g., no draft exists).
  - [ ] 3.7 Implement create draft calendar event tool
    - [ ] 3.7.1 Define a LiteLLM tool for creating or updating the active draft calendar event for a thread (no office-service call).
    - [ ] 3.7.2 Support parameters: thread id, event details (title, time, attendees, etc.).
    - [ ] 3.7.3 Store the draft in the history manager or a dedicated draft store, ensuring only one active draft per thread.
    - [ ] 3.7.4 On chat response, return the current active draft (if any) in the response payload.
    - [ ] 3.7.5 Add unit tests for create draft calendar event tool, including edge cases (e.g., draft already exists, update draft).
  - [ ] 3.8 Implement delete draft calendar event tool
    - [ ] 3.8.1 Define a LiteLLM tool for deleting the active draft calendar event for a thread (no office-service call).
    - [ ] 3.8.2 Support parameters: thread id.
    - [ ] 3.8.3 Remove the draft from the history manager or draft store.
    - [ ] 3.8.4 On chat response, ensure the draft is no longer present in the response payload.
    - [ ] 3.8.5 Add unit tests for delete draft calendar event tool, including edge cases (e.g., no draft exists).
  - [ ] 3.9 Implement create draft calendar change tool
    - [ ] 3.9.1 Define a LiteLLM tool for creating or updating the active draft calendar change for a thread (no office-service call).
    - [ ] 3.9.2 Support parameters: thread id, change details.
    - [ ] 3.9.3 Store the draft in the history manager or a dedicated draft store, ensuring only one active draft per thread.
    - [ ] 3.9.4 On chat response, return the current active draft (if any) in the response payload.
    - [ ] 3.9.5 Add unit tests for create draft calendar change tool, including edge cases (e.g., draft already exists, update draft).
  - [ ] 3.10 Implement delete draft calendar change tool
    - [ ] 3.10.1 Define a LiteLLM tool for deleting the active draft calendar change for a thread (no office-service call).
    - [ ] 3.10.2 Support parameters: thread id.
    - [ ] 3.10.3 Remove the draft from the history manager or draft store.
    - [ ] 3.10.4 On chat response, ensure the draft is no longer present in the response payload.
    - [ ] 3.10.5 Add unit tests for delete draft calendar change tool, including edge cases (e.g., no draft exists).
  - [ ] 3.11 Integrate all tools with LiteLLM agent and ensure correct registration and invocation.
  - [ ] 3.12 Add integration tests for LiteLLM agent with all tools and tool command schema.

- [ ] 4. Implement history manager
  - [ ] 4.1 Define database schema for history manager
    - [ ] 4.1.1 Define ORM models (e.g., SQLAlchemy) for `threads`, `messages`, and `drafts` tables.
    - [ ] 4.1.2 Ensure `drafts` table enforces one active draft per thread per type (unique constraint).
    - [ ] 4.1.3 Add fields for efficient retrieval (e.g., indexes on user_id, thread_id, updated_at).
    - [ ] 4.1.4 Add migration scripts or initial schema (e.g., Alembic, Prisma, or raw SQL).
  - [ ] 4.2 Implement thread and message storage/retrieval
    - [ ] 4.2.1 Implement functions to create, update, and list threads for a user.
    - [ ] 4.2.2 Implement functions to append and retrieve messages for a thread.
    - [ ] 4.2.3 Implement efficient history queries (e.g., pagination, ordering).
  - [ ] 4.3 Implement draft storage/retrieval
    - [ ] 4.3.1 Implement functions to create, update, and delete drafts for a thread and type.
    - [ ] 4.3.2 Ensure only one active draft per thread per type is allowed.
    - [ ] 4.3.3 Integrate draft logic with LiteLLM tools for create/delete/update.
    - [ ] 4.3.4 Ensure drafts are returned with chat responses as needed.
  - [ ] 4.4 Integrate history manager with API endpoints for chat and thread management.
  - [ ] 4.5 Add unit tests for all history manager operations, including edge cases (e.g., concurrent draft updates, missing threads).

- [ ] 5. Implement context module
  - [ ] 5.1 Define context condensation strategy based on OpenHands Context Condensation (see design doc).
  - [ ] 5.2 Implement `context_module.py` to:
    - [ ] 5.2.1 Select relevant messages and data from thread history and external sources.
    - [ ] 5.2.2 Summarize or condense long histories to fit LLM context window.
    - [ ] 5.2.3 Support dynamic context selection based on user input and thread state.
    - [ ] 5.2.4 Provide API for chat flow to request context for a given thread/user.
  - [ ] 5.3 Integrate context module with chat endpoint and LiteLLM agent.
  - [ ] 5.4 Add unit tests for context selection, condensation, and edge cases (e.g., very long threads).

- [ ] 6. Implement LLM usage tracking
  - [ ] 6.1 Define database schema/model for LLM usage tracking (fields: user_id, thread_id, message_id, provider, model, input_tokens, output_tokens, created_at).
  - [ ] 6.2 Implement `llm_usage.py` to:
    - [ ] 6.2.1 Record usage for each LLM invocation (batch input, new input, output tokens, provider, model, user, timestamp).
    - [ ] 6.2.2 Provide functions to query usage by user, thread, or time period.
  - [ ] 6.3 Integrate usage tracking with chat endpoint and LiteLLM calls.
  - [ ] 6.4 Add unit tests for usage tracking and reporting.

- [ ] 7. Implement feedback module
  - [ ] 7.1 Define database schema/model for feedback (fields: user_id, thread_id, message_id, feedback, created_at).
  - [ ] 7.2 Implement `feedback.py` to:
    - [ ] 7.2.1 Store thumbs up/down feedback for a given response.
    - [ ] 7.2.2 Provide functions to retrieve feedback for analytics or review.
  - [ ] 7.3 Integrate feedback module with feedback API endpoint.
  - [ ] 7.4 Add unit tests for feedback storage, retrieval, and edge cases (e.g., duplicate feedback, missing message).

- [ ] 8. Integrate with office-service and handle authentication/authorization
  - [ ] 8.1 Implement HTTP client logic to call office-service endpoints from LiteLLM tools.
  - [ ] 8.2 Forward user tokens to office-service for authorization.
  - [ ] 8.3 Handle and propagate errors from office-service.
  - [ ] 8.4 Add integration tests for office-service interactions.

- [ ] 9. Implement error handling, testing, and observability
  - [ ] 9.1 Implement consistent error response schema and error handling middleware.
  - [ ] 9.2 Add logging for requests, errors, and LLM/tool invocations.
  - [ ] 9.3 Add metrics for LLM usage (input/output tokens, latency).
  - [ ] 9.4 Write unit tests for all modules and API endpoints.
  - [ ] 9.5 Write integration tests for end-to-end chat flows.
  - [ ] 9.6 Ensure log structure supports future integration with observability tools.

