# Vespa Query Service Maturity Tasks

This document outlines the tasks needed to bring the `services/vespa_query` service up to the standards outlined in the new service guide.

## Overview

The `vespa_query` service is well-structured but needs alignment with the project's dependency management, service registration, and configuration standards. Since this service doesn't use a database, database-related improvements are not needed.

## Tasks

### 1. Dependency Management Issues
- [x] Convert `pyproject.toml` from `setuptools` to `poetry` format
- [x] Follow the project's UV/poetry dependency management pattern
- [x] Organize dependencies into proper groups (dependencies, dev-dependencies)

### 2. Missing Essential Dependencies
- [x] Add `httpx` for HTTP client testing (currently only has `aiohttp`)
- [x] Ensure all dependencies follow the version constraints from the new service guide

### 3. Configuration Management
- [ ] Verify API key configuration for inter-service authentication is properly implemented
- [ ] Add service URL configuration for inter-service communication
- [ ] Ensure all configuration follows the `services.common.settings` pattern

### 4. Service Registration Incomplete
- [x] Add service to environment variable scripts
- [x] Add environment variables to `.example.env`
- [x] Create `Dockerfile.vespa-query`
- [x] Ensure service is properly registered in all relevant startup scripts

### 5. API Key Authentication Missing
- [x] Implement `verify_api_key` dependency as shown in the new service guide
- [x] Add API key configuration in settings
- [x] Apply API key validation to all endpoints that require inter-service communication

### 6. Port Assignment Conflict
- [x] Change service port from 9002 to 8006 (or next available port in 8000s range)
- [x] Update all references to the port in configuration files
- [x] Ensure no port conflicts with other services

### 7. Health Check Improvements
- [x] Add Vespa connectivity check to health endpoint (external service dependency)
- [x] Implement proper health check configuration with timeout settings
- [x] Add health check interval and timeout configuration to settings

### 8. Error Handling
- [x] Replace basic `HTTPException` usage with standardized error classes from `services.common.http_errors`
- [x] Add proper error details and correlation IDs
- [x] Implement consistent error handling across all endpoints

### 9. Missing Service Integration
- [ ] Add integration with Express Gateway
- [ ] Configure service URL for gateway integration
- [ ] Implement proper service discovery setup

### 10. Test Dependencies
- [ ] Add `httpx` for HTTP client testing
- [ ] Ensure test structure follows project patterns
- [ ] Add comprehensive test coverage for all endpoints

## Notes

- **Database-related improvements are NOT needed** since this service doesn't use a database
- The service is already correctly using `services.common.settings.BaseSettings`
- Focus should be on dependency management, service registration, and integration standards

## Success Criteria

- [ ] Service follows all new service guide standards
- [ ] Service is properly registered in all startup and configuration scripts
- [ ] Service uses port 8006 (or appropriate port in 8000s range)
- [ ] Service has proper API key authentication
- [ ] Service integrates with Express Gateway
- [ ] All tests pass and follow project patterns
- [ ] Service can be started using the standard startup scripts
