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

**Tech**: Python 3.11+, FastAPI, PostgreSQL, Redis, Next.js, NextAuth, LangChain, OpenAI, Docker

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

- **Auth**: NextAuth (frontend) + service-to-service API keys
- **Communication**: Frontend → Next.js API routes → Backend services
- **Testing**: `pytest` with async support, `fakeredis`/`aiosqlite` for isolation
- **Style**: Black, isort, ruff, mypy (Python); ESLint (TypeScript)

## URLs
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Services: port 8000 (individual), `/api/proxy/...` (via Next.js)