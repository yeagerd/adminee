#!/bin/bash

# Briefly Development Utilities with UV
# Common development commands optimized with UV

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to check if virtual environment exists
check_venv() {
    if [ ! -d ".venv" ]; then
        print_error "Virtual environment not found. Please run ./scripts/dev-setup.sh first"
        exit 1
    fi
}

# Function to activate virtual environment
activate_venv() {
    source .venv/bin/activate
}

# Function to run tests
run_tests() {
    check_venv
    activate_venv
    
    local test_type=${1:-"all"}
    
    case $test_type in
        "all")
            print_status "Running all tests..."
            uv run tox
            ;;
        "fast")
            print_status "Running fast tests..."
            uv run tox -e test-fast
            ;;
        "coverage")
            print_status "Running tests with coverage..."
            uv run tox -e test-cov
            ;;
        "user")
            print_status "Running user service tests..."
            uv run python -m pytest services/user/tests/ -v
            ;;
        "chat")
            print_status "Running chat service tests..."
            uv run python -m pytest services/chat/tests/ -v
            ;;
        "office")
            print_status "Running office service tests..."
            uv run python -m pytest services/office/tests/ -v
            ;;
        *)
            print_error "Unknown test type: $test_type"
            echo "Available test types: all, fast, coverage, user, chat, office"
            exit 1
            ;;
    esac
}

# Function to run linting
run_lint() {
    check_venv
    activate_venv
    
    local lint_type=${1:-"all"}
    
    case $lint_type in
        "all")
            print_status "Running all linting checks..."
            uv run tox -e lint
            ;;
        "format")
            print_status "Running formatting checks..."
            uv run tox -e format
            ;;
        "fix")
            print_status "Fixing formatting issues..."
            uv run tox -e fix
            ;;
        "ruff")
            print_status "Running Ruff linting..."
            uv run ruff check services/
            ;;
        "black")
            print_status "Running Black formatting..."
            uv run black --check --diff services/
            ;;
        "isort")
            print_status "Running isort import sorting..."
            uv run isort --check-only --diff services/
            ;;
        *)
            print_error "Unknown lint type: $lint_type"
            echo "Available lint types: all, format, fix, ruff, black, isort"
            exit 1
            ;;
    esac
}

# Function to run type checking
run_typecheck() {
    check_venv
    activate_venv
    
    local strict=${1:-"false"}
    
    if [ "$strict" = "true" ]; then
        print_status "Running strict type checking..."
        uv run tox -e typecheck-strict
    else
        print_status "Running type checking..."
        uv run tox -e typecheck
    fi
}

# Function to add dependencies
add_dependency() {
    check_venv
    activate_venv
    
    local package=$1
    local service=${2:-"root"}
    
    if [ "$service" = "root" ]; then
        print_status "Adding dependency to root project: $package"
        uv add "$package"
    else
        print_status "Adding dependency to $service service: $package"
        cd "services/$service"
        uv add "$package"
        cd ../..
    fi
    
    print_success "Dependency added successfully"
}

# Function to update dependencies
update_dependencies() {
    check_venv
    activate_venv
    
    print_status "Updating dependencies..."
    uv lock --upgrade
    uv pip install -e .
    uv pip install -e services/chat
    uv pip install -e services/user
    uv pip install -e services/office
    uv pip install -e services/common
    uv pip install -e services/vector-db
    uv pip install -e ".[dev]"
    
    print_success "Dependencies updated successfully"
}

# Function to run database migrations
run_migrations() {
    check_venv
    activate_venv
    
    local service=${1:-"all"}
    
    case $service in
        "all")
            print_status "Running migrations for all services..."
            cd services/user && uv run alembic upgrade head && cd ../..
            cd services/chat && uv run alembic upgrade head && cd ../..
            cd services/office && uv run alembic upgrade head && cd ../..
            ;;
        "user")
            print_status "Running user service migrations..."
            cd services/user && uv run alembic upgrade head && cd ../..
            ;;
        "chat")
            print_status "Running chat service migrations..."
            cd services/chat && uv run alembic upgrade head && cd ../..
            ;;
        "office")
            print_status "Running office service migrations..."
            cd services/office && uv run alembic upgrade head && cd ../..
            ;;
        *)
            print_error "Unknown service: $service"
            echo "Available services: all, user, chat, office"
            exit 1
            ;;
    esac
    
    print_success "Migrations completed successfully"
}

# Function to show help
show_help() {
    echo "Briefly Development Utilities with UV"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  test [type]           Run tests (all, fast, coverage, user, chat, office)"
    echo "  lint [type]           Run linting (all, format, fix, ruff, black, isort)"
    echo "  typecheck [strict]    Run type checking (add 'true' for strict mode)"
    echo "  add <package> [service] Add dependency (service: root, user, chat, office)"
    echo "  update                Update all dependencies"
    echo "  migrate [service]     Run database migrations (service: all, user, chat, office)"
    echo "  help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 test fast"
    echo "  $0 lint fix"
    echo "  $0 typecheck true"
    echo "  $0 add fastapi user"
    echo "  $0 migrate chat"
}

# Main script logic
case ${1:-"help"} in
    "test")
        run_tests "$2"
        ;;
    "lint")
        run_lint "$2"
        ;;
    "typecheck")
        run_typecheck "$2"
        ;;
    "add")
        if [ -z "$2" ]; then
            print_error "Package name is required"
            exit 1
        fi
        add_dependency "$2" "$3"
        ;;
    "update")
        update_dependencies
        ;;
    "migrate")
        run_migrations "$2"
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 