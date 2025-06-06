# Chat Service Design Document

## Overview

The `chat-service` is a backend microservice responsible for providing conversational AI capabilities to the Briefly application. It exposes an API for chat interactions, manages conversation threads, integrates with other services (such as `office-service`), and tracks LLM usage and user feedback. The service is built using Python and leverages LangChain for LLM orchestration and tool integration.

---

## 1. API Endpoints

### 1.1. Chat Endpoint
- **POST /chat**
    - **Input:**
        - `user_id` (from Next.js API proxy, e.g., Clerk ID)
        - `thread_id` (optional; blank to start a new thread)
        - `user_input` (string)
    - **Output:**
        - `response` (LLM-generated chat response)
        - `tool_commands` (list of tool actions for the frontend)
        - `thread_id` (ID of the thread, new or existing)

### 1.2. Thread Management
- **GET /threads**
    - Returns a list of threads for the user (thread IDs, titles, last updated, etc.)
- **GET /threads/{thread_id}/history**
    - Returns the full message history for a given thread

### 1.3. Feedback
- **POST /feedback**
    - **Input:**
        - `user_id`
        - `thread_id`
        - `message_id` or `response_id`
        - `feedback` (e.g., thumbs up/down)
    - **Output:**
        - Success/failure

---

## 2. Core Modules

### 2.1. LangChain Integration
- Uses LangChain to orchestrate LLM calls and tool usage.
- Defines custom tools for:
    - **Data Retrieval:**
        - Get calendar, email, notes, and documents from `office-service` via HTTP API.
    - **Data Creation/Modification:**
        - Create/delete draft email
        - Create/delete draft calendar event
        - Create/delete draft calendar change
    - Only one active draft per thread is allowed (enforced by the service).

### 2.2. History Manager
- Stores and retrieves user chat history and thread metadata.
- Supports:
    - Appending new messages to a thread
    - Retrieving full history for a thread
    - Listing all threads for a user
- Storage backend: PostgreSQL (preferred), with thread/message tables.

### 2.3. Context Module
- Implements context condensation as described in [OpenHands Context Condensation](https://www.all-hands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents).
- Dynamically selects and summarizes relevant context from user history and external data for each LLM invocation.

### 2.4. LLM Usage Measurement
- Tracks per-invocation usage:
    - Batch input tokens
    - New input tokens
    - Output tokens
    - Provider
    - Model
    - User ID
    - Timestamp
- Stores usage data for analytics and cost tracking.

### 2.5. Feedback API
- Receives and stores user feedback (thumbs up/down) on responses.
- Associates feedback with user, thread, and message/response.

---

## 3. Integration with Office-Service
- All data retrieval and modification tools interact with `office-service` via REST API.
- Service discovery via Docker Compose DNS (e.g., `http://office-service:<port>`).
- Handles authentication/authorization using tokens passed from the API proxy.

---

## 4. Security & Authentication
- All endpoints require authentication (validated via API proxy, e.g., Clerk session).
- Sensitive actions (e.g., creating/deleting drafts) are authorized per user.
- No sensitive tokens are logged.

---


---

## 5. Data Models (MVP)

For the MVP, the following PostgreSQL tables are required:
- **threads**: `id` (PK), `user_id`, `title`, `created_at`, `updated_at`
- **messages**: `id` (PK), `thread_id` (FK), `user_id`, `role` (user/assistant/tool), `content`, `created_at`, `tool_commands` (JSON, nullable)
- **feedback**: `id` (PK), `user_id`, `thread_id`, `message_id`, `feedback` (enum: up/down), `created_at`
- **llm_usage**: `id` (PK), `user_id`, `thread_id`, `message_id`, `provider`, `model`, `input_tokens`, `output_tokens`, `created_at`

These schemas can be iterated on, but are sufficient for MVP chat, history, feedback, and usage tracking.

---

## 6. Tool Command Schema (MVP)

Tool commands returned to the frontend will use a standardized JSON format:
```json
{
  "tool": "<tool_name>",
  "action": "<action>",
  "parameters": { ... },
  "status": "pending|success|error",
  "message": "<optional details>"
}
```
- Example: `{ "tool": "calendar", "action": "create_event", "parameters": { ... }, "status": "pending" }`
- For MVP, only commands relevant to the frontend (e.g., draft creation, deletion) are returned; others are handled server-side.

---

## 7. Error Handling (MVP)

- All API endpoints return errors in a consistent JSON format:
```json
{
  "error": {
    "type": "<error_type>",
    "message": "<human-readable message>",
    "details": { ... }
  }
}
```
- HTTP status codes are used appropriately (e.g., 400 for bad request, 401 for unauthorized, 500 for server error).
- For MVP, error types include: `validation_error`, `auth_error`, `not_found`, `llm_error`, `tool_error`, `internal_error`.

---

## 8. Authentication/Authorization (MVP)

- All endpoints require a valid user token (e.g., Clerk JWT) passed via the API proxy in the `Authorization` header.
- The service validates the token using Clerk's backend SDK or via a shared secret/public key.
- User identity (`user_id`) is extracted from the token and used for all data access and downstream service calls.
- When calling `office-service`, the same user token is forwarded in the request headers for authorization.

---

## 9. LLM Provider Abstraction (MVP)

- For MVP, a single LLM provider/model (e.g., OpenAI GPT-4) is used, configured via environment variables.
- The codebase is structured to allow easy addition of other providers/models (e.g., via a provider registry or factory pattern).
- Provider/model used is recorded in the `llm_usage` table for each invocation.

---

## 10. Testing & Observability (MVP)

- **Testing:**
    - Unit tests for API endpoints, history manager, and tool integrations.
    - Integration tests for end-to-end chat flows.
    - Use of test database or mocks for database interactions.
- **Observability:**
    - Basic logging of requests, errors, and LLM/tool invocations.
    - Metrics for LLM usage (input/output tokens, latency).
    - For MVP, advanced tracing/monitoring is not required, but log structure should support future integration with tools like Sentry or Prometheus.

---

## 11. Areas of Concern / Open Questions
- **Concurrency:** Ensure thread safety and data consistency when handling simultaneous requests to the same thread (e.g., locking, race conditions in message and draft management).
- **Rate Limiting:** Implement per-user rate limiting to prevent abuse of LLM resources and API endpoints.
- **Error Handling:** Maintain robust error reporting and logging for failed tool calls, LLM errors, and integration failures with `office-service`.
- **Tool Command Schema:** Continue to standardize and evolve the tool command format as new tool types and frontend requirements emerge.
- **Draft Management:** Enforce the "one active draft per thread" rule and handle draft expiration, cleanup, and edge cases (e.g., abandoned drafts).
- **Data Privacy & Security:** Ensure user data isolation, secure token handling, and compliance with privacy best practices. Avoid logging sensitive data.
- **Scalability:** Design the service and database to handle high user concurrency and LLM throughput, with a path to horizontal scaling.
- **LLM Provider Abstraction:** Prepare for future support of multiple LLM providers/models, including configuration, selection, and usage tracking.
- **Testing Coverage:** Maintain comprehensive automated tests for API endpoints, tool integrations, and context condensation logic.
- **Observability:** Provide actionable logging, metrics, and error tracking to support debugging, monitoring, and future integration with observability platforms.
- **Integration Robustness:** Ensure reliable and secure communication with `office-service` and other dependencies, including token forwarding and error propagation.

---

## 12. Future Enhancements
- **Advanced Feedback:** Support for freeform feedback, message-level ratings, or reporting issues.
- **Asynchronous Tool Execution:** For long-running tool actions, support async workflows.
- **Rich Context Sources:** Integrate additional context sources (e.g., CRM, external docs).
- **User Personalization:** Adapt LLM behavior based on user preferences/history.
- **Visibility:** Use a websocket to stream the LLM output, reducing perceived latency.
- **Voice:** Support real-time conversation.

---

## 13. References
- [OpenHands Context Condensation](https://www.all-hands.dev/blog/openhands-context-condensensation-for-more-efficient-ai-agents)
- [LangChain Documentation](https://python.langchain.com/)

*This document is a living specification and should be updated as the service evolves.*
