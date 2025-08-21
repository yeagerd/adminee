# Type Generation Workflow

This document describes the automated workflow for generating TypeScript types from Python Pydantic models, ensuring a single source of truth between backend and frontend.

## Overview

Our system automatically generates TypeScript types from FastAPI/Pydantic models using OpenAPI schemas. This eliminates manual type duplication and ensures consistency between backend and frontend.

## Architecture

```
Python Backend (Pydantic Models)
           ↓
    FastAPI OpenAPI Schema
           ↓
    OpenAPI JSON Schema
           ↓
TypeScript Type Generation
           ↓
    Frontend Type Files
```

## Automated Workflow

### GitHub Actions (CI/CD)

The main workflow is automated via GitHub Actions in `.github/workflows/generate-types.yml`:

1. **Triggers**: Automatically runs when Python service files change
2. **Schema Generation**: Generates OpenAPI schemas for all services
3. **Type Generation**: Creates TypeScript types from schemas
4. **Auto-commit**: Commits changes and creates PRs automatically
5. **Notifications**: Slack notifications for success/failure

### Manual Development Workflow

For development and testing, use the provided scripts:

#### 1. Generate OpenAPI Schemas

```bash
# Generate schemas for all services
./scripts/generate-openapi-schemas.sh

# Generate schema for specific service
./scripts/generate-openapi-schemas.sh chat

# Verbose output
./scripts/generate-openapi-schemas.sh --verbose
```

#### 2. Update TypeScript Types

```bash
# Update types for all services
./scripts/update-types.sh

# Update types for specific service
./scripts/update-types.sh chat

# Force regeneration (ignore timestamps)
./scripts/update-types.sh --force

# Clean and regenerate all types
./scripts/update-types.sh --clean

# Verbose output
./scripts/update-types.sh --verbose
```

#### 3. Validate Generated Types

```bash
# Validate all types
./scripts/validate-types.sh

# Validate specific service
./scripts/validate-types.sh chat

# Strict TypeScript checking
./scripts/validate-types.sh --strict

# Run integration tests
./scripts/validate-types.sh --integration

# Verbose output
./scripts/validate-types.sh --verbose
```

## Service Structure

Each service follows this structure:

```
services/
├── chat/
│   ├── main.py              # FastAPI app
│   ├── models/              # Pydantic models
│   ├── schemas/             # API schemas
│   └── openapi/
│       └── schema.json      # Generated OpenAPI schema
├── meetings/
│   ├── main.py
│   ├── models/
│   ├── schemas/
│   └── openapi/
│       └── schema.json
└── ...

frontend/
└── types/
    └── api/
        ├── chat/            # Generated TypeScript types
        ├── meetings/        # Generated TypeScript types
        └── ...
```

## Generated Type Structure

Each service generates:

```
frontend/types/api/{service}/
├── index.ts                 # Main exports
├── models/                  # Data models
│   ├── UserResponse.ts
│   ├── ChatRequest.ts
│   └── ...
├── services/                # API service classes
│   ├── ChatService.ts
│   ├── UsersService.ts
│   └── ...
└── core/                    # Core utilities
    ├── ApiError.ts
    ├── ApiRequestOptions.ts
    └── ...
```

## Usage in Frontend

### Importing Types

```typescript
// Import specific types
import type { UserResponse, ChatRequest } from '@/types/api/chat';

// Import services
import { ChatService } from '@/types/api/chat';

// Import from main index
import type { UserResponse } from '@/types/api';
```

### Using Generated Services

```typescript
import { ChatService } from '@/types/api/chat';

const chatService = new ChatService('http://localhost:8000');

// Use generated methods
const response = await chatService.chatStream({
    message: "Hello",
    user_id: "123"
});
```

## Development Guidelines

### Backend Changes

1. **Update Pydantic Models**: Modify models in `services/{service}/models/`
2. **Update API Endpoints**: Modify endpoints in `services/{service}/api/`
3. **Test Locally**: Run `./scripts/generate-openapi-schemas.sh {service}`
4. **Commit Changes**: Push to trigger automatic type generation

### Frontend Changes

1. **Use Generated Types**: Always import from `@/types/api/*`
2. **No Manual Types**: Don't create manual interfaces for API data
3. **Type Validation**: Run `./scripts/validate-types.sh` before committing
4. **Update Components**: Use generated types in React components

### Adding New Services

1. **Create Service Structure**:
   ```bash
   mkdir -p services/new-service/{models,schemas,api}
   ```

2. **Add FastAPI App**:
   ```python
   # services/new-service/main.py
   from fastapi import FastAPI
   
   app = FastAPI(title="New Service")
   
   @app.get("/health")
   async def health():
       return {"status": "healthy"}
   ```

3. **Generate Schema**:
   ```bash
   ./scripts/generate-openapi-schemas.sh new-service
   ```

4. **Generate Types**:
   ```bash
   ./scripts/update-types.sh new-service
   ```

## Troubleshooting

### Common Issues

1. **Schema Generation Fails**:
   - Check Python dependencies are installed
   - Verify FastAPI app structure
   - Check for syntax errors in Python code

2. **Type Generation Fails**:
   - Ensure `openapi-typescript-codegen` is installed
   - Check OpenAPI schema is valid JSON
   - Verify Node.js/npm are available

3. **Type Compilation Errors**:
   - Run `./scripts/validate-types.sh --strict`
   - Check for missing dependencies
   - Verify TypeScript configuration

4. **Import Errors**:
   - Check generated types exist
   - Verify import paths are correct
   - Run `./scripts/validate-types.sh --integration`

### Debug Commands

```bash
# Check service structure
ls -la services/*/main.py

# Verify OpenAPI schemas
find services -name "schema.json" -exec jq . {} \;

# Check generated types
ls -la frontend/types/api/*/

# Test TypeScript compilation
cd frontend && npx tsc --noEmit

# Run full validation
./scripts/validate-types.sh --verbose --strict
```

## Best Practices

1. **Single Source of Truth**: Always define types in Pydantic models
2. **Automatic Updates**: Let CI/CD handle type generation
3. **Validation**: Run validation scripts before committing
4. **Documentation**: Keep this guide updated with changes
5. **Testing**: Test type integration in development

## Monitoring

- **GitHub Actions**: Monitor workflow runs in Actions tab
- **Slack Notifications**: Receive success/failure alerts
- **Type Validation**: Regular validation in development
- **Error Tracking**: Monitor TypeScript compilation errors

## Support

For issues with the type generation workflow:

1. Check this documentation first
2. Run validation scripts to identify problems
3. Check GitHub Actions logs for CI/CD issues
4. Review generated schemas and types
5. Contact the development team

## Future Improvements

- [ ] Add type compatibility checking
- [ ] Implement breaking change detection
- [ ] Add performance monitoring
- [ ] Create type migration tools
- [ ] Add schema versioning
