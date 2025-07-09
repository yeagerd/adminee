# Briefly

AI-powered calendar and task management platform with intelligent scheduling, document management, and seamless office integration.

## Architecture

- **Frontend:** Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui components
- **Backend Services:** Python microservices with FastAPI
  - `services/chat/` - AI chat and workflow automation
  - `services/user/` - User management and authentication
  - `services/office/` - Email, calendar, and file integration
  - `services/common/` - Shared utilities and configurations
  - `services/vector_db/` - Vector database operations
- **Database:** PostgreSQL
- **Vector Database:** Pinecone

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
   ./scripts/start-services.sh
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

4. **Set up Database Migrations:**

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
   # Remove the database file (e.g., for user service)
   rm services/user/user_service.db
   
   # Re-run the migration to create fresh tables
   alembic -c services/user/alembic.ini upgrade head
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
  - The **PostgreSQL database** will be running on port `5432` (accessible as `db:5432` from other services within the Docker network, or `localhost:5432` from the host).
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
    # Virtual environment is already activated by setup-dev.sh
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
  "service": "user-management-service",
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
  4. **Deploy Database:** Provision a managed PostgreSQL instance (e.g., AWS RDS, Google Cloud SQL) or deploy PostgreSQL as a container (with persistent storage).
  5. **Deploy Vector Database:** Ensure your Pinecone index is set up and accessible.
  6. **Deploy Backend Services:** Deploy the containerized backend services, configuring them to connect to the database, Pinecone, and each other.
  7. **Build and Deploy Frontend:** Build the Next.js application and deploy it. Configure it to point to the deployed API gateway/proxy endpoint.
  8. **Set up Authentication:** Ensure Microsoft OAuth and Clerk (if used) are configured with the correct redirect URIs and credentials for the deployed environment.

- *(Specific deployment scripts and platform guides will be added as the target deployment environment is finalized.)*

## Tracing

### Manual Instrumentation (Optional)

For additional custom tracing, use the shared telemetry module:

```python
from services.common import setup_telemetry, get_tracer, add_span_attributes

# Set up telemetry (optional - already done by opentelemetry-instrument)
setup_telemetry("user-management", "1.0.0")

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
