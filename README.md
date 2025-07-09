# Briefly

AI-powered calendar and task management platform with intelligent scheduling, document management, and seamless office integration.

## Architecture

- **Frontend:** Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui components
- **Backend Services:** Python microservices with FastAPI
  - `services/chat/` - AI chat and workflow automation
  - `services/user/` - User management and authentication
  - `services/office/` - Email, calendar, and file integration
  - `services/common/` - Shared utilities and configurations
  - `services/vector-db/` - Vector database operations
- **Database:** PostgreSQL
- **Vector Database:** Pinecone

## Development with UV

This project uses [UV](https://github.com/astral-sh/uv) for Python package management and virtual environment management. UV is a fast, reliable, and secure package manager and resolver written in Rust.

### Prerequisites

- Python 3.12 or higher
- [UV](https://github.com/astral.sh/uv#installation) installed on your system

### Quick Start

1. **Install UV** (if not already installed):
   ```bash
   curl -sSf https://astral.sh/uv/install.sh | sh
   ```

2. **Set up development environment**:
   ```bash
   ./scripts/dev-setup.sh
   ```

3. **Start all services**:
   ```bash
   ./scripts/start-services.sh
   ```

### Development Workflow

#### Using UV Commands

**Install dependencies:**
```bash
# Install all project dependencies including dev dependencies
uv sync

# Install specific service in development mode
uv pip install -e services/chat

# Install with development dependencies
uv pip install -e ".[dev]"
```

**Run services:**
```bash
# Start individual services
uv run python -m uvicorn services.chat.main:app --port 8001 --reload
uv run python -m uvicorn services.user.main:app --port 8000 --reload
uv run python -m uvicorn services.office.app.main:app --port 8002 --reload

# Or use the convenience script
./scripts/start-services.sh
```

**Run tests:**
```bash
# Run all tests
uv run tox

# Run specific test environments
uv run tox -e lint     # Linting
uv run tox -e typecheck # Type checking
uv run tox -e test     # Unit tests
```

#### Using Development Utilities

We provide a comprehensive development utilities script for common tasks:

```bash
# Run tests
./scripts/dev-utils.sh test fast
./scripts/dev-utils.sh test coverage
./scripts/dev-utils.sh test user

# Run linting
./scripts/dev-utils.sh lint fix
./scripts/dev-utils.sh lint format

# Type checking
./scripts/dev-utils.sh typecheck true  # Strict mode

# Add dependencies
./scripts/dev-utils.sh add fastapi user
./scripts/dev-utils.sh add pytest --dev

# Update dependencies
./scripts/dev-utils.sh update

# Run migrations
./scripts/dev-utils.sh migrate all
./scripts/dev-utils.sh migrate chat
```

### Service-Specific Setup

#### Chat Service

The Chat Service provides AI-powered conversation and workflow automation.

**Start the service:**
```bash
cd services/chat
uv run python -m uvicorn main:app --reload
```

**API Endpoints:**
- `POST /chat` - Start a new chat session
- `POST /chat/{thread_id}/messages` - Send a message
- `GET /chat/{thread_id}/messages` - Get chat history

#### User Management Service

The User Management Service handles user authentication, profiles, and preferences.

**Start the service:**
```bash
cd services/user
uv run python -m uvicorn main:app --reload
```

**API Endpoints:**
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update user profile
- `GET /users/me/preferences` - Get user preferences

#### Office Service

The Office Service provides unified access to email, calendar, and file data across Google and Microsoft providers.

**Start the service:**
```bash
cd services/office
uv run python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API Endpoints:**
- **Health:** `GET /health` - Service health check
- **Email:** 
  - `GET /email/messages` - Get unified email messages
  - `GET /email/messages/{id}` - Get specific email message
  - `POST /email/send` - Send email
- **Calendar:**
  - `GET /calendar/events` - Get calendar events
  - `POST /calendar/events` - Create calendar event
  - `DELETE /calendar/events/{id}` - Delete calendar event
- **Files:**
  - `GET /files/` - List files
  - `GET /files/search` - Search files
  - `GET /files/{id}` - Get specific file

### Testing

**Run all tests:**
```bash
uv run tox
```

**Run specific test categories:**
```bash
# Fast tests (stop on first failure)
./scripts/dev-utils.sh test fast

# Coverage tests
./scripts/dev-utils.sh test coverage

# Service-specific tests
./scripts/dev-utils.sh test user
./scripts/dev-utils.sh test chat
./scripts/dev-utils.sh test office
```

**Type checking:**
```bash
# Standard type checking
./scripts/dev-utils.sh typecheck

# Strict type checking
./scripts/dev-utils.sh typecheck true
```

**Linting and formatting:**
```bash
# Check formatting
./scripts/dev-utils.sh lint format

# Fix formatting issues
./scripts/dev-utils.sh lint fix

# Run all linting checks
./scripts/dev-utils.sh lint all
```

### Database Management

**Run migrations:**
```bash
# All services
./scripts/dev-utils.sh migrate all

# Specific service
./scripts/dev-utils.sh migrate chat
./scripts/dev-utils.sh migrate user
./scripts/dev-utils.sh migrate office
```

### Dependency Management

**Add new dependencies:**
```bash
# Add to root project
./scripts/dev-utils.sh add fastapi

# Add to specific service
./scripts/dev-utils.sh add sqlalchemy user

# Add development dependency
./scripts/dev-utils.sh add pytest --dev
```

**Update dependencies:**
```bash
./scripts/dev-utils.sh update
```

### Environment Configuration

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure environment variables:**
   - Database URLs for each service
   - API keys for external services
   - OAuth credentials for Google/Microsoft
   - Pinecone API key and environment

### Docker Development

**Build and run with Docker Compose:**
```bash
docker compose up --build
```

**Individual service containers:**
```bash
# Build specific service
docker build -f Dockerfile.chat-service -t briefly-chat .

# Run service
docker run -p 8001:8000 briefly-chat
```

### Performance Benefits with UV

- **10-100x faster** dependency resolution
- **Better caching** for repeated operations
- **Reliable dependency resolution** with lock files
- **Faster virtual environment** creation
- **Improved development workflow** with `uv run`

### Troubleshooting

**Common issues:**

1. **Virtual environment not found:**
   ```bash
   ./scripts/dev-setup.sh
   ```

2. **Dependency conflicts:**
   ```bash
   ./scripts/dev-utils.sh update
   ```

3. **Test failures:**
   ```bash
   ./scripts/dev-utils.sh test fast
   ```

4. **Type checking errors:**
   ```bash
   ./scripts/dev-utils.sh typecheck
   ```

For more detailed troubleshooting, check the service-specific documentation in each service directory.

