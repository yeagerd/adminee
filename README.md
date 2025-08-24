# Briefly

AI-powered calendar and task management platform with intelligent scheduling, document management, and seamless office integration.

<img width="715" height="537" alt="Screenshot 2025-07-29 at 7 45 52 AM" src="https://github.com/user-attachments/assets/6e53d632-9e31-49f4-8d0f-578ac3c67230" />


## Architecture

- **Frontend:** Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui components
- **API Gateway:** Express.js with NextAuth JWT validation, rate limiting, and security filtering
- **Backend Services:** Python microservices with FastAPI
  - `services/chat/` - AI chat and workflow automation
  - `services/user/` - User management and authentication
  - `services/office/` - Email, calendar, and file integration
  - `services/common/` - Shared utilities and configurations

- **Database:** PostgreSQL

## AI Tool System

Briefly features a dynamic tool discovery system that allows AI agents to discover, understand, and execute tools at runtime. This provides a flexible, extensible way to add new capabilities without modifying agent code.

### Tool Categories

- **Data Retrieval** (`data_retrieval`) - Access user data from integrated services (calendar, email, notes, documents)
- **Draft Management** (`draft_management`) - Create and manage draft content for emails and calendar events  
- **Search** (`search`) - Search across various data sources with semantic and traditional search
- **Web Search** (`web_search`) - External web search capabilities
- **Utility** (`utility`) - Helper functions for data processing, validation, and formatting

### Key Features

- **Dynamic Discovery**: Agents can discover available tools using `list_tools()`
- **Self-Documenting**: Each tool provides complete API specifications via `get_tool_info(tool_id)`
- **Secure by Design**: User context is pre-bound to prevent tampering
- **Extensible**: New tools can be registered without agent code changes
- **Categorized**: Tools are organized by functionality for easy discovery

### Documentation

- **[Tool Discovery Implementation](documentation/tool_discovery_implementation.md)** - Complete implementation guide
- **[Tool Categories Reference](documentation/tool_categories.md)** - Detailed reference for all tool categories
- **[Tool Registration Guide](documentation/tool_registration_guide.md)** - Step-by-step guide for adding new tools

> 📚 **New to Briefly?** See our [New Service Guide](documentation/new-service-guide.md) for creating new microservices.

### Service Communication Flow

```
User → NextAuth BFF → Express Gateway → Backend Services
  ↓         ↓              ↓                ↓
OAuth   JWT Token    Auth Validation   Business Logic
Login   Session      Rate Limiting     API Key Auth
```

## Development with UV

This project uses [UV](https://github.com/astral-sh/uv) for Python package management and virtual environment management. UV is a fast, reliable, and secure package manager and resolver written in Rust.

### Prerequisites

- Python 3.12 or higher
- [UV](https://github.com/astral.sh/uv#installation) installed on your system
- **Docker and Docker Compose:** Ensure Docker Desktop or Docker Engine with Compose plugin is installed. [Install Docker](https://docs.docker.com/get-docker/) or `brew install docker colima`
- **VS Code Dev Containers Extension:** If using VS Code, install the "Dev Containers" extension by Microsoft (`ms-vscode-remote.remote-containers`).
- **Node.js and npm/yarn:** For interacting with the frontend directly or managing global Node packages. `nvm` is recommended for managing Node versions. (Existing setup instruction: Install nvm, install node v18.18.2)
- **Git:** For version control.

### Quick Start

1. **Set up development environment**:
   ```bash
   ./install.sh
   ```

2. **Start all services**:
   ```bash
   ./scripts/start-all-services.sh
   ```

### Development Workflow

#### Using UV Commands

**Install dependencies:**
```bash
# Install all project dependencies including dev dependencies (see install.sh)
uv sync --all-packages --all-extras --active

# Install specific service in development mode
uv pip install -e services/chat

# Install with development dependencies
uv pip install -e ".[dev]"

# Find outdated packages
uv pip list --outdated | cat
```

**Run services:**
```bash
# Start all services (recommended)
./scripts/start-all-services.sh

# Start individual services
uv run python -m uvicorn services.chat.main:app --port 8001 --reload
uv run python -m uvicorn services.user.main:app --port 8000 --reload
uv run python -m uvicorn services.office.app.main:app --port 8002 --reload

# Start gateway separately
./scripts/gateway-start.sh
```

**Run tests:**
```bash
# Run all tests
nox -s test

# Run specific test environments
nox -s lint        # Linting
nox -s typecheck   # Type checking
nox -s test        # Unit tests
```

#### Development Commands

Use UV directly for common development tasks:

```bash
# Run tests
nox -s test                  # All tests
nox -s test_fast            # Fast tests
nox -s test_cov             # Coverage tests

# Run service-specific tests
uv run python -m pytest services/user/tests/ -v
uv run python -m pytest services/chat/tests/ -v
uv run python -m pytest services/office/tests/ -v

# Linting and formatting
nox -s lint                  # All linting
nox -s format                # Format check

# Type checking
nox -s typecheck             # Standard
nox -s typecheck_strict      # Strict mode

# OpenAPI Schema Generation
./scripts/generate-openapi-schemas.sh        # Generate schemas for all services
./scripts/generate-openapi-schemas.sh chat   # Generate schema for specific service

# Frontend Type Generation
cd frontend
./scripts/generate-types.sh                  # Generate TypeScript types from schemas
npm run typecheck                           # Verify generated types are valid

# Add dependencies
uv add fastapi               # Add to root
uv add sqlalchemy --project services/user  # Add to service

# Update dependencies
uv lock --upgrade
uv sync --all-packages --all-extras --active

# Run migrations
alembic -c services/user/alembic.ini upgrade head
alembic -c services/chat/alembic.ini upgrade head
alembic -c services/office/alembic.ini upgrade head
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
nox -s test
```

**Run specific test categories:**
```bash
# Fast tests (stop on first failure)
nox -s test_fast

# Coverage tests
nox -s test_cov

# Service-specific tests
uv run python -m pytest services/user/tests/ -v
uv run python -m pytest services/chat/tests/ -v
uv run python -m pytest services/office/tests/ -v
```

**Type checking:**
```bash
# Standard type checking
nox -s typecheck

# Strict type checking
nox -s typecheck_strict
```

**Linting and formatting:**
```bash
# Check formatting
nox -s format

# Run all linting checks
nox -s lint
```

### Database Management

**PostgreSQL Setup and Management:**

For detailed PostgreSQL setup, environment configuration, and database management instructions, see [postgres/README.md](postgres/README.md).

**Quick Start:**
```bash
# Start PostgreSQL with local environment
./scripts/postgres-start.sh --env-file .env.postgres.local

# Stop PostgreSQL
./scripts/postgres-stop.sh
```

**Run migrations:**
```bash
# All services
alembic -c services/user/alembic.ini upgrade head
alembic -c services/chat/alembic.ini upgrade head
alembic -c services/office/alembic.ini upgrade head

# Specific service
alembic -c services/chat/alembic.ini upgrade head
alembic -c services/user/alembic.ini upgrade head
alembic -c services/office/alembic.ini upgrade head
```

### Dependency Management

**Add new dependencies:**
```bash
# Add to root project
uv add fastapi

# Add to specific service
uv add sqlalchemy --project services/user

# Add development dependency
uv add pytest --dev
```

**Update dependencies:**
```bash
uv lock --upgrade
uv sync --all-packages --all-extras --active
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

### Local Development Setup

#### Getting Started

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd briefly
   ```

2. **Set up Environment Variables:**
   - Copy the example environment file:
     ```bash
     cp .env.example .env
     ```
   - Open `.env` and fill in the required values for `DB_URL_*`, `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, Microsoft OAuth credentials (`AZURE_AD_CLIENT_ID`, etc.), and other required configuration.

3. **Launch the Development Environment:**

   **Using VS Code Dev Containers (Recommended):**
   1. Open the cloned repository folder in VS Code.
   2. When prompted, click "Reopen in Container". This will build and start the services defined in `docker-compose.yml` and configure your VS Code environment.

   **Using Docker Compose directly:**
   If using `colima`, first run `colima start`
   ```bash
   docker compose up --build
   ```
   This will build the images and start all services. The main application (including frontend and proxied backend) will typically be available at `http://localhost:3000`.

   You can then stop it with
   ```bash
   docker compose down
   ```

4. **Set up Database:**

   **PostgreSQL Setup:**
   For detailed PostgreSQL setup and environment configuration, see [postgres/README.md](postgres/README.md).

   **Quick Start:**
   ```bash
   # Start PostgreSQL with local environment
   ./scripts/postgres-start.sh --env-file .env.postgres.local
   ```

   **Database Migrations:**
   All services use Alembic for database schema management. Run migrations from the repository root:

   ```bash
   # Office Service (port 8002)
   alembic -c services/office/alembic.ini upgrade head

   # User Management Service (port 8000)
   alembic -c services/user/alembic.ini upgrade head

   # Chat Service (port 8001)
   alembic -c services/chat/alembic.ini upgrade head
   ```

   **Important:** Always run migrations from the repository root, not from within service directories. The database URLs in your `.env` file are configured to work from the root directory.

   **For Development (Fresh Start):**
   If you need to reset a service's database:
   ```bash
   # Start fresh PostgreSQL (WILL DELETE DATA)
   ./scripts/postgres-start.sh --fresh-install --env-file .env.postgres.local

   # Re-run the migration to create fresh tables
   alembic -c services/office/alembic.ini upgrade head
   alembic -c services/user/alembic.ini upgrade head
   alembic -c services/chat/alembic.ini upgrade head
   ```

   **For Production:**
   - Never delete production databases
   - Always backup before running migrations
   - Test migrations on staging first
   - Use `alembic stamp head` if tables exist but migration history is missing

   **Creating New Migrations:**
   ```bash
   # Generate a new migration for a service
   alembic -c services/office/alembic.ini revision --autogenerate -m "Add new table"

   # Apply the new migration
   alembic -c services/office/alembic.ini upgrade head
   ```

   **Checking Migration Status:**
   ```bash
   # Check current migration status
   alembic -c services/office/alembic.ini current

   # List all migrations
   alembic -c services/office/alembic.ini history
   ```

#### Running the Application

- Once the dev container or Docker Compose setup is running:
  - The **Next.js frontend** should be accessible at `http://localhost:3000`.
  - The **PostgreSQL database** will be running on port `5432` (accessible as `db:5432` from other services within the Docker network, or `localhost:5432` from the host). For PostgreSQL setup and management, see [postgres/README.md](postgres/README.md).
  - Backend services will be running on their respective ports and are typically accessed via the Next.js proxy at `localhost:3000/api/proxy/...`.

#### Local Testing

- **Frontend Testing:** (Details to be added - e.g., Jest, React Testing Library, Cypress)
  ```bash
  # Example: Navigate to frontend directory and run tests
  # cd app/ # or services/frontend if that structure is adopted
  # yarn test
  ```
- **Backend Service Testing:**
  - Each service in `services/` should have its own test suite within a `tests/` subdirectory (e.g., `services/office/tests/`).
  - To run tests for a specific service, you might execute commands within its container or set up test scripts.
    ```bash
    # Office Service Testing:
    cd services/office
    # Virtual environment is already activated by install.sh
    pytest                    # Run all tests
    pytest tests/test_integration.py  # Run integration tests only

    # Run type checking and linting
    mypy services/
    ./fix                     # Auto-fix lint issues
    tox -p auto              # Run full test matrix in parallel
    ```
- **API Testing:** Use tools like Postman, Insomnia, or `curl` to test API endpoints exposed by the Next.js proxy and individual backend services.

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
   ./install.sh
   ```

2. **Dependency conflicts:**
   ```bash
   uv lock --upgrade
   uv sync --all-packages --all-extras --active
   ```

3. **Test failures:**
   ```bash
   nox -s test_fast
   ```

4. **Type checking errors:**
   ```bash
   nox -s typecheck
   ```

For more detailed troubleshooting, check the service-specific documentation in each service directory.

## Logging Configuration

The application uses structured logging that can be configured for development or production use:

### For Human-Readable Logs (Development)

Set the log format to "text" for easier reading during development:

```bash
export LOG_FORMAT=text
export LOG_LEVEL=INFO
./scripts/start-services.sh
```

Or create a `.env` file:
```
LOG_FORMAT=text
LOG_LEVEL=DEBUG
```

### For Machine-Readable Logs (Production)

Use JSON format for structured logging in production:

```bash
export LOG_FORMAT=json
export LOG_LEVEL=INFO
```

### Log Format Examples

**Text format (human-readable):**
```
2025-06-20 06:58:14 - services.user.security.encryption - INFO - Token decrypted successfully [user_id=demo_user]
```

**JSON format (machine-readable):**
```json
{
  "timestamp": "2025-06-20T06:58:14.258Z",
  "level": "INFO",
  "logger": "services.user.security.encryption",
  "message": "Token decrypted successfully",
  "service": "user-service",
  "user_id": "demo_user"
}
```

## Building for Production

- **Frontend (Next.js):**
  ```bash
  # cd app/ (or services/frontend)
  # yarn build
  ```
  This typically creates an optimized build in a `.next` directory.

- **Backend Services (Docker Images):**
  - The individual Dockerfiles (`Dockerfile.office-service`, `Dockerfile.chat-service`, `Dockerfile.user-service`) are used to build production-ready images for each service.
  - Example build command for the calendar service:
    ```bash
    docker build -t briefly/office-service:latest -f Dockerfile.office-service .
    ```
  - These images can then be pushed to a container registry (e.g., Docker Hub, AWS ECR, GCP Artifact Registry).

## Deployment

- **General Strategy:** Deploy backend services as containers (e.g., to Kubernetes, AWS ECS, Google Cloud Run). Deploy the Next.js frontend to a platform optimized for Node.js/React applications (e.g., Vercel, Netlify, or also as a container).

- **Steps (Conceptual):**
  1. **Build Docker Images:** Use the service-specific Dockerfiles to build images for `office-service`, `chat-service`, and `user-service`.
  2. **Push Images to Registry:** Push the built images to a container registry.
  3. **Configure Environment Variables:** Set up environment variables (from `.env` content) in the deployment environment for each service (e.g., database connection strings, API keys).
  4. **Deploy Database:** Provision a managed PostgreSQL instance (e.g., AWS RDS, Google Cloud SQL) or deploy PostgreSQL as a container (with persistent storage). See [postgres/README.md](postgres/README.md) for detailed setup instructions.
5. **Deploy Vector Database:** Ensure your Pinecone index is set up and accessible.
  6. **Deploy Backend Services:** Deploy the containerized backend services, configuring them to connect to the database, Pinecone, and each other.
  7. **Build and Deploy Frontend:** Build the Next.js application and deploy it. Configure it to point to the deployed API gateway/proxy endpoint.
  8. **Set up Authentication:** Ensure Microsoft OAuth is configured with the correct redirect URIs and credentials for the deployed environment.

- *(Specific deployment scripts and platform guides will be added as the target deployment environment is finalized.)*

## Tracing

### Manual Instrumentation (Optional)

For additional custom tracing, use the shared telemetry module:

```python
from services.common import setup_telemetry, get_tracer, add_span_attributes

# Set up telemetry (optional - already done by opentelemetry-instrument)
setup_telemetry("user", "1.0.0")

# Get a tracer for custom spans
tracer = get_tracer(__name__)

# Create custom spans
with tracer.start_as_current_span("custom_operation") as span:
    add_span_attributes(user_id="123", operation="data_processing")
    # Your code here
```

### Environment Variables

#### Production Configuration

For production environments with Google Cloud Trace:

```bash
ENVIRONMENT=production
GOOGLE_CLOUD_PROJECT_ID=your-project-id
```

#### Development Configuration

For development, OpenTelemetry runs with basic configuration:

```bash
ENVIRONMENT=development
```

## Python Conventions

* Do not introduce any testconf.py files
* Do not use relative imports
* Do not load or create globals on module load

## Unit Testing

- Unit tests are co-located with the services or in dedicated test directories (e.g., `services/office/tests/`).
- **Running Python Unit Tests (e.g., for `office-service` with pytest):**
  ```bash
  # Ensure you are in the dev container or have the Python environment activated
  # pytest services/office/
  ```
  Or via Docker Compose if tests need service dependencies:
  ```bash
  docker-compose exec app pytest services/office/
  ```
- **Running Node.js Unit Tests (e.g., for `email-service` with Jest/Mocha):**
  ```bash
  # cd services/email-service/
  # yarn test
  ```
  Or via Docker Compose:
  ```bash
  docker-compose exec app yarn --cwd /workspace/services/email-service test
  ```
- *(Further details on specific test commands and frameworks for each service will be added as they are implemented.)*

## Code Quality and Linting (tox)

- We use [tox -p auto](https://tox.readthedocs.io/) to automate code formatting, linting, and type checking for all Python backend services under `services/`.
- `tox -e fix` will run [black](https://black.readthedocs.io/), [isort](https://pycqa.github.io/isort/), [ruff](https://docs.astral.sh/ruff/), and [mypy](https://mypy-lang.org/) on all Python code in the `services/` directory.

#### To run all checks:

```bash
# From the project root
tox
```

- This will run formatting checks, linting, and type checking for all Python services.
- You can also run a specific environment, e.g.:
  - `tox -e format` (run black and isort checks)
  - `tox -e lint` (run ruff linter)
  - `tox -e typecheck` (run mypy type checks)

```bash
# Find slow tests (from the project root)
python -m pytest --durations=10 -q -n auto
```

## Contributing

(To be added: Guidelines for contributing, code style, pull request process, etc.)

## License

See `LICENSE`

## Unified Authentication Patterns

- **User-facing endpoints:**
  - Use NextAuth JWT authentication (user logs in via OAuth, receives JWT)
  - JWT is attached as a Bearer token in the Authorization header for all API calls
  - Gateway and backend services validate JWT and extract user context
  - Endpoints use `/me` or header-based user extraction (no user_id in path/query)

- **Service-to-service and background jobs:**
  - Use API key authentication (API key in `X-API-Key` or `Authorization` header)
  - Internal endpoints use `/internal` prefix and require API key
  - API keys are stored in environment variables (never exposed to frontend)

- **Environment variables:**
  - `NEXTAUTH_SECRET`: Used to sign/validate JWTs (must match between frontend, gateway, and backend)
  - `API_FRONTEND_USER_KEY`, `API_FRONTEND_CHAT_KEY`, `API_FRONTEND_OFFICE_KEY`: API keys for service-to-service auth
  - `NEXT_PUBLIC_GATEWAY_URL`: Used by frontend to call the gateway

- **Endpoint patterns:**
  - `/me` endpoints for user-facing actions (require JWT)
  - `/internal` endpoints for service-to-service (require API key)

- **Key setup steps:**
  - Set all required secrets and API keys in your environment (see .env.example and ENVIRONMENT_SETUP.md)
  - Never expose API keys to client-side code
  - Rotate secrets/keys as needed for security

See `frontend/ENVIRONMENT_SETUP.md` and service READMEs for more details.
