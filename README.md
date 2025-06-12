# Briefly

Gives you a smart daily brief, fast and concise. A personal assistant for everyone. Calendar intelligence and beyond.

## Overview

Briefly is a multi-service application designed to provide intelligent calendar summaries and task management. It integrates with Microsoft Graph API for calendar data, uses a RAG pipeline with Pinecone for contextual information, and delivers notifications via an email service.

Key components include:
- **Frontend:** Next.js application (`app/`)
- **API Gateway:** Next.js API routes (`app/api/proxy/`)
- **Backend Services:**
    - `services/office-service/` (Python/FastAPI)
    - `services/chat-service/` (Python/FastAPI)
    - `services/auth-service/` (Node.js) (or maybe Python)
- **Database:** PostgreSQL
- **Vector Database:** Pinecone

## Office Service

The Office Service is a FastAPI-based microservice that provides unified access to email, calendar, and file data across Google and Microsoft providers. It handles OAuth token management, data normalization, caching, and provides RESTful APIs for frontend consumption.

### Key Features

- **Unified API:** Single endpoints for email, calendar, and files across Google and Microsoft
- **Data Normalization:** Converts provider-specific responses to standardized models
- **Caching:** Redis-based caching for improved performance
- **Error Handling:** Comprehensive error handling with structured logging
- **Token Management:** Secure OAuth token retrieval and caching
- **Async Architecture:** Built with FastAPI and async/await for high performance

### Office Service Setup

1. **Navigate to the service directory:**
   ```bash
   cd services/office_service
   ```

2. **Set up unified development environment:**
   ```bash
   ./setup-dev.sh
   ```
   This script will:
   - Create a unified virtual environment for all services
   - Install all dependencies from all services
   - Install shared packages in editable mode

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Start the service:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Office Service API Endpoints

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

### Office Service Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_integration.py     # Integration tests
pytest tests/test_api_email.py       # Email API tests
pytest tests/test_token_manager.py   # Token management tests

# Run with coverage
pytest --cov=services.office_service

# Type checking
mypy services/

# Linting and formatting
./fix                    # Auto-fix issues
tox -p auto             # Full test matrix
```

## Local Development Setup

### Prerequisites

- **Docker and Docker Compose:** Ensure Docker Desktop or Docker Engine with Compose plugin is installed. [Install Docker](https://docs.docker.com/get-docker/) or `brew install docker colima`
- **VS Code Dev Containers Extension:** If using VS Code, install the "Dev Containers" extension by Microsoft (`ms-vscode-remote.remote-containers`).
- **Node.js and npm/yarn:** For interacting with the frontend directly or managing global Node packages. `nvm` is recommended for managing Node versions. (Existing setup instruction: Install nvm, install node v18.18.2)
- **Git:** For version control.

### Getting Started

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd briefly
    ```

2.  **Set up Environment Variables:**
    -   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    -   Open `.env` and fill in the required values for `DATABASE_URL`, `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, Microsoft OAuth credentials (`AZURE_AD_CLIENT_ID`, etc.), and ``.

3.  **Launch the Development Environment:**

    *   **Using VS Code Dev Containers (Recommended):**
        1.  Open the cloned repository folder in VS Code.
        2.  When prompted, click "Reopen in Container". This will build and start the services defined in `docker-compose.yml` and configure your VS Code environment.
    *   **Using Docker Compose directly:**
        If using `colima`, first run `colima start`
        ```bash
        docker compose up --build
        ```
        This will build the images and start all services. The main application (including frontend and proxied backend) will typically be available at `http://localhost:3000`.

        You can then stop it with
        ```bash
        docker compose down
        ```

### Running the Application

-   Once the dev container or Docker Compose setup is running:
    -   The **Next.js frontend** should be accessible at `http://localhost:3000`.
    -   The **PostgreSQL database** will be running on port `5432` (accessible as `db:5432` from other services within the Docker network, or `localhost:5432` from the host).
    -   Backend services (e.g., Calendar Service) will be running on their respective ports (e.g., `8000`) and are typically accessed via the Next.js proxy at `localhost:3000/api/proxy/...`.

### Local Testing

-   **Frontend Testing:** (Details to be added - e.g., Jest, React Testing Library, Cypress)
    ```bash
    # Example: Navigate to frontend directory and run tests
    # cd app/ # or services/frontend if that structure is adopted
    # yarn test
    ```
-   **Backend Service Testing:**
    -   Each service in `services/` should have its own test suite within a `tests/` subdirectory (e.g., `services/office-service/tests/`).
    -   To run tests for a specific service, you might execute commands within its container or set up test scripts.
        ```bash
        # Office Service Testing:
        cd services/office_service
        # Virtual environment is already activated by setup-dev.sh
        pytest                    # Run all tests
        pytest tests/test_integration.py  # Run integration tests only
        
        # Run type checking and linting
        mypy services/
        ./fix                     # Auto-fix lint issues
        tox -p auto              # Run full test matrix in parallel
        ```
-   **API Testing:** Use tools like Postman, Insomnia, or `curl` to test API endpoints exposed by the Next.js proxy and individual backend services.

## Building for Production

-   **Frontend (Next.js):**
    ```bash
    # cd app/ (or services/frontend)
    # yarn build
    ```
    This typically creates an optimized build in a `.next` directory.

-   **Backend Services (Docker Images):**
    -   The individual Dockerfiles (`Dockerfile.office-service`, `Dockerfile.chat-service`, `Dockerfile.user-service`) are used to build production-ready images for each service.
    -   Example build command for the calendar service:
        ```bash
        docker build -t briefly/office-service:latest -f Dockerfile.office-service .
        ```
    -   These images can then be pushed to a container registry (e.g., Docker Hub, AWS ECR, GCP Artifact Registry).

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

## Unit Testing

-   Unit tests are co-located with the services or in dedicated test directories (e.g., `services/office-service/tests/`).
-   **Running Python Unit Tests (e.g., for `office-service` with pytest):**
    ```bash
    # Ensure you are in the dev container or have the Python environment activated
    # pytest services/office-service/
    ```
    Or via Docker Compose if tests need service dependencies:
    ```bash
    docker-compose exec app pytest services/office-service/
    ```
-   **Running Node.js Unit Tests (e.g., for `email-service` with Jest/Mocha):**
    ```bash
    # cd services/email-service/
    # yarn test 
    ```
    Or via Docker Compose:
    ```bash
    docker-compose exec app yarn --cwd /workspace/services/email-service test
    ```
-   *(Further details on specific test commands and frameworks for each service will be added as they are implemented.)*

## Deployment

-   **General Strategy:** Deploy backend services as containers (e.g., to Kubernetes, AWS ECS, Google Cloud Run). Deploy the Next.js frontend to a platform optimized for Node.js/React applications (e.g., Vercel, Netlify, or also as a container).

-   **Steps (Conceptual):**
    1.  **Build Docker Images:** Use the service-specific Dockerfiles to build images for `office-service`, `chat-service`, and `user-service`.
    2.  **Push Images to Registry:** Push the built images to a container registry.
    3.  **Configure Environment Variables:** Set up environment variables (from `.env` content) in the deployment environment for each service (e.g., database connection strings, API keys).
    4.  **Deploy Database:** Provision a managed PostgreSQL instance (e.g., AWS RDS, Google Cloud SQL) or deploy PostgreSQL as a container (with persistent storage).
    5.  **Deploy Vector Database:** Ensure your Pinecone index is set up and accessible.
    6.  **Deploy Backend Services:** Deploy the containerized backend services, configuring them to connect to the database, Pinecone, and each other.
    7.  **Build and Deploy Frontend:** Build the Next.js application and deploy it. Configure it to point to the deployed API gateway/proxy endpoint.
    8.  **Set up Authentication:** Ensure Microsoft OAuth and Clerk (if used) are configured with the correct redirect URIs and credentials for the deployed environment.

-   *(Specific deployment scripts and platform guides will be added as the target deployment environment is finalized.)*

## Code Quality and Linting (tox)

-   We use [tox -p auto](https://tox.readthedocs.io/) to automate code formatting, linting, and type checking for all Python backend services under `services/`.
-   `tox -e fix` will run [black](https://black.readthedocs.io/), [isort](https://pycqa.github.io/isort/), [ruff](https://docs.astral.sh/ruff/), and [mypy](https://mypy-lang.org/) on all Python code in the `services/` directory.

#### To run all checks:

```bash
# From the project root
tox
```

-   This will run formatting checks, linting, and type checking for all Python services.
-   You can also run a specific environment, e.g.:
    -   `tox -e format` (run black and isort checks)
    -   `tox -e lint` (run ruff linter)
    -   `tox -e typecheck` (run mypy type checks)


```bash
# Find slow tests (from the project root)
python -m pytest --durations=10 -q -n auto
```


## Contributing

(To be added: Guidelines for contributing, code style, pull request process, etc.)

## License

See `LICENSE`

---