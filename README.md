# Briefly

Gives you a smart daily brief, fast and concise. A personal assistant for everyone. Calendar intelligence and beyond.

## Overview

Briefly is a multi-service application designed to provide intelligent calendar summaries and task management. It integrates with Microsoft Graph API for calendar data, uses a RAG pipeline with Pinecone for contextual information, and delivers notifications via an email service.

Key components include:
- **Frontend:** Next.js application (`app/`)
- **API Gateway:** Next.js API routes (`app/api/proxy/`)
- **Backend Services:**
    - `services/calendar-service/` (Python/FastAPI)
    - `services/email-service/` (Node.js)
    - `services/auth-service/` (Node.js)
- **Database:** PostgreSQL
- **Vector Database:** Pinecone

## Local Development Setup

### Prerequisites

- **Docker and Docker Compose:** Ensure Docker Desktop or Docker Engine with Compose plugin is installed. [Install Docker](https://docs.docker.com/get-docker/)
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
    -   Open `.env` and fill in the required values for `DATABASE_URL`, `PINECONE_API_KEY`, `PINECONE_ENVIRONMENT`, Microsoft OAuth credentials (`AZURE_AD_CLIENT_ID`, etc.), and `NEXTAUTH_SECRET`.

3.  **Launch the Development Environment:**

    *   **Using VS Code Dev Containers (Recommended):**
        1.  Open the cloned repository folder in VS Code.
        2.  When prompted, click "Reopen in Container". This will build and start the services defined in `docker-compose.yml` and configure your VS Code environment.
    *   **Using Docker Compose directly:**
        ```bash
        docker-compose up --build
        ```
        This will build the images and start all services. The main application (including frontend and proxied backend) will typically be available at `http://localhost:3000`.

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
    -   Each service in `services/` should have its own test suite within a `tests/` subdirectory (e.g., `services/calendar-service/tests/`).
    -   To run tests for a specific service, you might execute commands within its container or set up test scripts.
        ```bash
        # Example: Run tests for calendar-service (assuming a Makefile or test runner)
        # docker-compose exec app python -m pytest services/calendar-service/tests
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
    -   The individual Dockerfiles (`Dockerfile.calendar-service`, `Dockerfile.email-service`, `Dockerfile.auth-service`) are used to build production-ready images for each service.
    -   Example build command for the calendar service:
        ```bash
        docker build -t briefly/calendar-service:latest -f Dockerfile.calendar-service .
        ```
    -   These images can then be pushed to a container registry (e.g., Docker Hub, AWS ECR, GCP Artifact Registry).

## Unit Testing

-   Unit tests are co-located with the services or in dedicated test directories (e.g., `services/calendar-service/tests/`).
-   **Running Python Unit Tests (e.g., for `calendar-service` with pytest):**
    ```bash
    # Ensure you are in the dev container or have the Python environment activated
    # pytest services/calendar-service/
    ```
    Or via Docker Compose if tests need service dependencies:
    ```bash
    docker-compose exec app pytest services/calendar-service/
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
    1.  **Build Docker Images:** Use the service-specific Dockerfiles to build images for `calendar-service`, `email-service`, and `auth-service`.
    2.  **Push Images to Registry:** Push the built images to a container registry.
    3.  **Configure Environment Variables:** Set up environment variables (from `.env` content) in the deployment environment for each service (e.g., database connection strings, API keys).
    4.  **Deploy Database:** Provision a managed PostgreSQL instance (e.g., AWS RDS, Google Cloud SQL) or deploy PostgreSQL as a container (with persistent storage).
    5.  **Deploy Vector Database:** Ensure your Pinecone index is set up and accessible.
    6.  **Deploy Backend Services:** Deploy the containerized backend services, configuring them to connect to the database, Pinecone, and each other.
    7.  **Build and Deploy Frontend:** Build the Next.js application and deploy it. Configure it to point to the deployed API gateway/proxy endpoint.
    8.  **Set up Authentication:** Ensure Microsoft OAuth and Clerk (if used) are configured with the correct redirect URIs and credentials for the deployed environment.

-   *(Specific deployment scripts and platform guides will be added as the target deployment environment is finalized.)*

## Contributing

(To be added: Guidelines for contributing, code style, pull request process, etc.)

## License

(To be added: Specify project license, e.g., MIT, Apache 2.0)

---
*Original create-next-app setup notes:*
* Install nvm
* Install node v18.18.2
* create-next-app@latest
