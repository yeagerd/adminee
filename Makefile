# Makefile for Briefly project with automated type generation workflow

.PHONY: help install types types-clean types-force types-validate types-full frontend-build frontend-dev frontend-test frontend-lint frontend-typecheck build-all test-all lint-all check-all clean

# Default target
help:
	@echo "Briefly Project - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Type Generation:"
	@echo "  types              - Generate types for all services"
	@echo "  types-clean        - Clean and regenerate all types"
	@echo "  types-force        - Force regeneration ignoring timestamps"
	@echo "  types-validate     - Validate generated types"
	@echo "  types-full         - Generate and validate types"
	@echo ""
	@echo "Frontend:"
	@echo "  frontend-build     - Build frontend with type generation"
	@echo "  frontend-dev       - Start frontend development server"
	@echo "  frontend-test      - Run frontend tests"
	@echo "  frontend-lint      - Run frontend linting"
	@echo "  frontend-typecheck - Run frontend type checking"
	@echo ""
	@echo "Full Pipeline:"
	@echo "  build-all          - Full build with types and frontend"
	@echo "  test-all           - Run all tests with type validation"
	@echo "  lint-all           - Run all linting and type checking"
	@echo "  check-all          - Full validation (types, lint, test)"
	@echo ""
	@echo "Utilities:"
	@echo "  install            - Install dependencies"
	@echo "  clean              - Clean generated files"
	@echo "  help               - Show this help message"

# Install dependencies
install:
	@echo "Installing dependencies..."
	@if [ -f "package.json" ]; then npm install; fi
	@if [ -d "frontend" ]; then cd frontend && npm install; fi
	@if [ -d "gateway" ]; then cd gateway && npm install; fi
	@echo "✅ Dependencies installed"

# Type generation targets
types:
	@echo "Generating types for all services..."
	@./scripts/generate-openapi-schemas.sh
	@./scripts/update-types.sh
	@echo "✅ Types generated"

types-clean:
	@echo "Cleaning and regenerating types..."
	@./scripts/generate-openapi-schemas.sh
	@./scripts/update-types.sh --clean
	@echo "✅ Types cleaned and regenerated"

types-force:
	@echo "Force regenerating types..."
	@./scripts/generate-openapi-schemas.sh
	@./scripts/update-types.sh --force
	@echo "✅ Types force regenerated"

types-validate:
	@echo "Validating generated types..."
	@./scripts/validate-types.sh
	@echo "✅ Types validated"

types-full: types types-validate

# Frontend targets
frontend-build: types-validate
	@echo "Building frontend..."
	@cd frontend && npm run build
	@echo "✅ Frontend built"

frontend-dev:
	@echo "Starting frontend development server..."
	@cd frontend && npm run dev

frontend-test:
	@echo "Running frontend tests..."
	@cd frontend && npm test
	@echo "✅ Frontend tests completed"

frontend-lint:
	@echo "Running frontend linting..."
	@cd frontend && npm run lint
	@echo "✅ Frontend linting completed"

frontend-typecheck:
	@echo "Running frontend type checking..."
	@cd frontend && npm run typecheck
	@echo "✅ Frontend type checking completed"

# Full pipeline targets
build-all: types-full frontend-build
	@echo "✅ Full build completed"

test-all: types-validate frontend-test
	@echo "✅ All tests completed"

lint-all: frontend-lint frontend-typecheck
	@echo "✅ All linting completed"

check-all: types-validate frontend-typecheck frontend-lint frontend-test
	@echo "✅ Full validation completed"

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	@rm -rf frontend/types/api
	@find services -name "openapi" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Generated files cleaned"

# Development workflow shortcuts
dev: types-validate frontend-dev
	@echo "✅ Development environment ready"

quick-build: types frontend-build
	@echo "✅ Quick build completed"

quick-test: types-validate frontend-test
	@echo "✅ Quick test completed"

# CI/CD pipeline targets
ci-types: types-full
	@echo "✅ CI type generation completed"

ci-build: ci-types frontend-build
	@echo "✅ CI build completed"

ci-test: ci-types frontend-test
	@echo "✅ CI test completed"

ci-full: ci-types frontend-build frontend-test
	@echo "✅ CI full pipeline completed"

# Service-specific type generation
types-chat:
	@echo "Generating types for chat service..."
	@./scripts/generate-openapi-schemas.sh chat
	@./scripts/update-types.sh chat
	@echo "✅ Chat service types generated"

types-meetings:
	@echo "Generating types for meetings service..."
	@./scripts/generate-openapi-schemas.sh meetings
	@./scripts/update-types.sh meetings
	@echo "✅ Meetings service types generated"

types-office:
	@echo "Generating types for office service..."
	@./scripts/generate-openapi-schemas.sh office
	@./scripts/update-types.sh office
	@echo "✅ Office service types generated"

types-user:
	@echo "Generating types for user service..."
	@./scripts/generate-openapi-schemas.sh user
	@./scripts/update-types.sh user
	@echo "✅ User service types generated"

types-shipments:
	@echo "Generating types for shipments service..."
	@./scripts/generate-openapi-schemas.sh shipments
	@./scripts/update-types.sh shipments
	@echo "✅ Shipments service types generated"

# Validation shortcuts
validate-chat:
	@echo "Validating chat service types..."
	@./scripts/validate-types.sh chat
	@echo "✅ Chat service types validated"

validate-meetings:
	@echo "Validating meetings service types..."
	@./scripts/validate-types.sh meetings
	@echo "✅ Meetings service types validated"

validate-office:
	@echo "Validating office service types..."
	@./scripts/validate-types.sh office
	@echo "✅ Office service types validated"

validate-user:
	@echo "Validating user service types..."
	@./scripts/validate-types.sh user
	@echo "✅ User service types validated"

validate-shipments:
	@echo "Validating shipments service types..."
	@./scripts/validate-types.sh shipments
	@echo "✅ Shipments service types validated"

# Debug and troubleshooting
debug-types:
	@echo "Debugging type generation..."
	@echo "Checking service schemas..."
	@find services -name "schema.json" -exec echo "Schema: {}" \;
	@echo "Checking generated types..."
	@find frontend/types/api -type d -exec echo "Types: {}" \;
	@echo "✅ Debug information displayed"

check-deps:
	@echo "Checking dependencies..."
	@echo "Node.js version: $(shell node --version 2>/dev/null || echo 'Not installed')"
	@echo "npm version: $(shell npm --version 2>/dev/null || echo 'Not installed')"
	@echo "Python version: $(shell python --version 2>/dev/null || echo 'Not installed')"
	@echo "✅ Dependency check completed"
