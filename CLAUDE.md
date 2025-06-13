# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Briefly** is a microservices calendar intelligence app with AI-powered meeting assistance. Architecture: Next.js frontend + 3 Python FastAPI services via Docker Compose.

## Services & Stack
- **Frontend**: Next.js 15.2.4 + TypeScript (`/frontend/`)
- **User Management**: FastAPI for profiles, OAuth tokens (`/services/user_management/`)
- **Office Service**: Unified Google/Microsoft calendar/email API (`/services/office_service/`)
- **Chat Service**: AI conversations with LLM integration (`/services/chat_service/`)
- **Vector DB**: Pinecone for RAG pipeline (`/services/vector-db/`)

**Tech**: Python 3.11+, FastAPI, PostgreSQL, Redis, Next.js, Clerk auth, LangChain, OpenAI, Docker

## Key Commands

### Code Quality (from project root)
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
cd services/{service}/
python -m venv venv && source venv/bin/activate
pip install -r ../../requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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