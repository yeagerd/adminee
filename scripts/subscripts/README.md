# Script Subscripts

This directory contains specialized scripts that are called by the main orchestration scripts.

## Purpose

The `scripts/subscripts/` directory organizes our script hierarchy to make it clear which scripts are:
- **Main entry points** (in `scripts/`)
- **Specialized tools** (in `scripts/subscripts/`)

## Scripts

### `generate-openapi-schemas.sh`
Generates OpenAPI schemas for all services by running each FastAPI application.

### `validate-types.sh`
Validates generated TypeScript types for all services.

### `update-types.sh`
Legacy script for updating types - use `../generate-api-schema.sh` instead.

## Usage

**Direct usage (not recommended):**
```bash
./scripts/subscripts/generate-openapi-schemas.sh
./scripts/subscripts/validate-types.sh
```

**Recommended usage (via main script):**
```bash
./scripts/generate-api-schema.sh                    # Full workflow
./scripts/generate-api-schema.sh --schema-only      # Schemas only
./scripts/generate-api-schema.sh --types-only       # Types only
```

## Why This Structure?

1. **Clear hierarchy**: Main scripts vs. specialized tools
2. **Single entry point**: `generate-api-schema.sh` orchestrates everything
3. **Maintainability**: Easier to understand dependencies
4. **Developer experience**: One command to rule them all

## Adding New Subscripts

When adding new specialized scripts:
1. Place them in `scripts/subscripts/`
2. Update the main `generate-api-schema.sh` to call them
3. Document their purpose here
