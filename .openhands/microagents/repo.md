# Briefly Repository

## Overview

Briefly is a multi-service application that provides intelligent calendar summaries and task management. It serves as a personal assistant that integrates with Microsoft Graph API for calendar data, uses a RAG (Retrieval-Augmented Generation) pipeline with Pinecone for contextual information, and delivers smart daily briefs.

## Architecture

The application follows a microservices architecture with the following components:

### Frontend
- **Technology**: Next.js 15 with React 19, TypeScript, Tailwind CSS
- **Location**: `frontend/`
- **Authentication**: Clerk integration for user management
- **UI Components**: Radix UI components with custom styling
- **Features**: Calendar interface, chat interface, task management, responsive design

### Backend Services

#### 1. Chat Service (`services/chat_service/`)
- **Technology**: Python/FastAPI
- **Purpose**: Handles AI-powered chat interactions and LLM integrations
- **Key Files**:
  - `main.py` - FastAPI application entry point
  - `api.py` - API route definitions
  - `llm_tools.py` - LLM integration utilities
  - `models.py` - Data models
  - `tests/` - Unit tests

#### 2. Office Service (`services/office_service/`)
- **Technology**: Python/FastAPI
- **Purpose**: Microsoft Graph API integration for calendar and office data
- **Key Files**:
  - `main.py` - FastAPI application entry point
  - `models.py` - Data models
  - `exceptions.py` - Custom exception handling
  - `providers/` - External service integrations
  - `services/` - Business logic

#### 3. User Service (`services/user_service/`)
- **Technology**: Node.js
- **Purpose**: User management and authentication
- **Key Files**:
  - `index.js` - Main service entry point
  - `microsoft-graph.js` - Microsoft Graph API client
  - `prisma-client.js` - Database client
  - `package.json` - Node.js dependencies

#### 4. Vector Database Service (`services/vector-db/`)
- **Technology**: Python
- **Purpose**: Pinecone integration for vector storage and retrieval
- **Key Files**:
  - `indexing_service.py` - Document indexing logic
  - `pinecone_client.py` - Pinecone API client

### Database
- **Primary Database**: PostgreSQL 15 (containerized)
- **Vector Database**: Pinecone (cloud service)
- **Schema**: Prisma schema defined in `services/db/schema.prisma`

## Development Environment

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.11+ (for backend services)
- Git

### Environment Variables
Copy `.env.example` to `.env` and configure:
- `DB_URL_*` - PostgreSQL connection string
- `PINECONE_API_KEY` - Pinecone API key
- `PINECONE_ENVIRONMENT` - Pinecone environment
- `AZURE_AD_CLIENT_ID`, `AZURE_AD_CLIENT_SECRET`, `AZURE_AD_TENANT_ID` - Microsoft OAuth
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` - Clerk authentication
- `NEXTAUTH_URL`, `NEXTAUTH_SECRET` - NextAuth configuration

### Running the Application

#### Using Docker Compose (Recommended)
```bash
# Start all services
docker compose up --build

# Stop services
docker compose down
```

#### Development Ports
- Frontend (Next.js): `http://localhost:3000`
- Backend APIs: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

#### Individual Service Development

**Frontend:**
```bash
cd frontend/
npm install
npm run dev
```

**Python Services:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run specific service (example: chat service)
cd services/chat_service/
uvicorn main:app --reload --port 8000
```

**User Service (Node.js):**
```bash
cd services/user_service/
npm install
node index.js
```

## Code Quality and Testing

### Python Services
The project uses `tox` for automated code quality checks:

```bash
# Run all checks (formatting, linting, type checking, tests)
tox

# Run specific checks
tox -e format    # Black and isort formatting
tox -e lint      # Ruff linting
tox -e typecheck # MyPy type checking
tox -e test      # Pytest unit tests
```

### Code Quality Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pytest**: Unit testing framework

### Frontend Testing
```bash
cd frontend/
npm run lint     # ESLint
npm run build    # Build verification
```

## Deployment

### Production Build

**Frontend:**
```bash
cd frontend/
npm run build
npm start
```

**Backend Services:**
Each service has its own Dockerfile:
- `Dockerfile.chat-service`
- `Dockerfile.office-service`
- `Dockerfile.user-service`

```bash
# Build service images
docker build -t briefly/chat-service -f Dockerfile.chat-service .
docker build -t briefly/office-service -f Dockerfile.office-service .
docker build -t briefly/user-service -f Dockerfile.user-service .
```

### Infrastructure Requirements
- Container orchestration (Kubernetes, Docker Swarm, or cloud container services)
- Managed PostgreSQL database
- Pinecone account and index
- Microsoft Azure AD application registration
- Clerk account for authentication

## Key Dependencies

### Python Backend
- **FastAPI**: Modern web framework for APIs
- **Ormar**: Async ORM for database operations
- **Pydantic**: Data validation and serialization
- **LiteLLM**: LLM integration library
- **Pinecone**: Vector database client
- **Alembic**: Database migrations
- **Uvicorn**: ASGI server

### Frontend
- **Next.js 15**: React framework with App Router
- **Clerk**: Authentication and user management
- **Radix UI**: Accessible component library
- **Tailwind CSS**: Utility-first CSS framework
- **React Hook Form**: Form handling
- **Zod**: Schema validation

### Development Tools
- **Tox**: Test automation
- **Docker**: Containerization
- **TypeScript**: Type safety for frontend
- **ESLint**: JavaScript/TypeScript linting

## Project Structure
```
briefly/
├── frontend/                 # Next.js frontend application
├── services/                 # Backend microservices
│   ├── chat_service/        # AI chat service (Python/FastAPI)
│   ├── office_service/      # Microsoft Graph integration (Python/FastAPI)
│   ├── user_service/        # User management (Node.js)
│   ├── vector-db/           # Pinecone integration (Python)
│   └── db/                  # Database schema
├── documentation/           # Technical documentation
├── planning/               # Project planning documents
├── tasks/                  # Development tasks and notes
├── docker-compose.yml      # Development environment
├── tox.ini                 # Python code quality configuration
├── requirements.txt        # Python dependencies
└── Dockerfile.*           # Service-specific Docker builds
```

## Getting Started

1. **Clone the repository**
2. **Set up environment variables** (copy `.env.example` to `.env`)
3. **Start development environment**: `docker compose up --build`
4. **Access the application**: `http://localhost:3000`
5. **Run tests**: `tox` (for Python services)

The application provides a modern, scalable architecture for building intelligent personal assistant features with calendar integration and AI-powered interactions.