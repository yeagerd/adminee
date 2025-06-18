# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Briefly** is a microservices calendar intelligence app with AI-powered meeting assistance. Architecture: Next.js frontend + 3 Python FastAPI services via Docker Compose.

## Services & Stack
- **Frontend**: Next.js 15.2.4 + TypeScript (`/frontend/`)
- **User Management**: FastAPI for profiles, OAuth tokens (`/services/user/`)
- **Office Service**: Unified Google/Microsoft calendar/email API (`/services/office/`)
- **Chat Service**: AI conversations with LLM integration (`/services/chat/`)
- **Vector DB**: Pinecone for RAG pipeline (`/services/vector-db/`)

**Tech**: Python 3.11+, FastAPI, PostgreSQL, Redis, Next.js, Clerk auth, LangChain, OpenAI, Docker

## Key Commands
From project root:

### Test and Code Quality
```bash
tox -e fix           # Auto-fix formatting/linting
tox -p auto          # Run all checks (format, lint, typecheck, test)
```

### Frontend
```bash
cd frontend/
npm run dev          # Start dev server
npm run build        # Production build
```

### Backend Services
```bash
source venv/bin/activate
./services/{service}/start.sh
```

### Database
```bash
cd services/{service}/
alembic upgrade head  # Apply migrations
```

## Development Patterns

- **Auth**: Clerk (frontend) + service-to-service API keys
- **Communication**: Frontend → Next.js API routes → Backend services
- **Testing**: `pytest` with async support, `fakeredis`/`aiosqlite` for isolation
- **Style**: Black, isort, ruff, mypy (Python); ESLint (TypeScript)

## URLs
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Services: port 8000 (individual), `/api/proxy/...` (via Next.js)

# Recent Improvements

## Thread ID Management and Draft Tracking Simplification (December 19, 2024)

### Problem
The chat service had two main issues with thread/draft management:
1. **Complex thread_id retrieval**: The `get_thread_id_from_context` function was overly complex, trying multiple ways to get thread_id from context
2. **LLM dependency for tracking**: The system relied on the LLM to keep track of thread/draft relationships instead of handling this programmatically

### Solution
Refactored the system to be more direct and programmatic:

#### DraftAgent Improvements
- **Removed complex context lookup**: Eliminated the `get_thread_id_from_context()` function and all its complex fallback logic
- **Direct thread_id storage**: DraftAgent now stores `thread_id` directly as `self.thread_id` and uses it consistently
- **Simplified tool creation**: Tools now access `self.thread_id` directly instead of going through context lookups
- **Cleaner initialization**: Thread ID is passed once during initialization and stored as the source of truth

#### WorkflowAgent Improvements  
- **Programmatic draft access**: Added methods like `get_current_drafts()`, `has_drafts()`, and `clear_all_drafts()`
- **Direct storage access**: Draft data is accessed directly from `_draft_storage` rather than relying on LLM context
- **Synchronous methods**: Added sync methods for easier programmatic access to draft data
- **Better separation of concerns**: LLM focuses on conversation, while draft tracking is handled programmatically

#### Key Benefits
- **Reliability**: No more complex context lookups that could fail
- **Performance**: Direct access to stored data instead of context traversal  
- **Maintainability**: Simple, direct code that's easy to understand
- **Separation of concerns**: LLM handles conversation, system handles data tracking

#### API Changes
```python
# New programmatic methods in WorkflowAgent:
agent.get_current_drafts()  # Returns dict of current drafts
agent.has_drafts()         # Boolean check for draft existence  
agent.clear_all_drafts()   # Programmatically clear all drafts

# DraftAgent now uses direct thread_id:
DraftAgent(thread_id=123)  # Thread ID stored directly, no context lookup needed
```

#### Migration Notes
- **No breaking changes**: Existing API methods still work
- **Backward compatible**: Old async `get_draft_data()` method preserved
- **Tests passing**: All existing tests continue to work
- **Demo updated**: New demo shows programmatic draft tracking