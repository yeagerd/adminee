# Briefly Meetings Service

This service provides AI-powered meeting scheduling, poll management, and calendar/email integration for Briefly.

## Running the Service

```bash
uv run python -m uvicorn main:app --reload --port 8003
```

## Running Migrations

```bash
alembic upgrade head
```

## Features
- AI-powered meeting poll creation
- Multi-platform calendar integration
- Poll response collection (web/email)
- Real-time poll status and analytics
