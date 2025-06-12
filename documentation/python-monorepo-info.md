# Shared Packages Setup for Briefly Services

This document explains the setup for shared `common` and `vector_db` packages across all services in the Briefly project.

## Overview

The setup provides:
- **Editable installs**: Changes to shared packages are immediately available to all services
- **Proper import resolution**: Standard Python import syntax works across services
- **VS Code IntelliSense**: Enhanced code completion and go-to-definition
- **Type checking**: mypy properly resolves imports from shared packages

## Quick Setup

Run the installation setup script from the repository root:

```bash
./setup-dev.sh
```

This script will:
- Create virtual environments for the main project and all services
- Install requirements for each service
- Install shared packages in editable mode for all services

## What Was Configured

### 1. Package Structure
- `services/common/`: Contains telemetry and shared utilities
- `services/vector-db/`: Contains vector database utilities (Pinecone client, indexing)

### 2. Setup Files Created
- `services/common/setup.py`: Makes common installable as a package
- `services/vector-db/setup.py`: Makes vector-db installable as `vector_db` package
- `services/vector-db/__init__.py`: Makes the directory a proper Python package

### 3. VS Code Configuration
Each service's `.vscode/settings.json` includes:
```json
{
  "python.defaultInterpreterPath": "venv/bin/python",
  "python.analysis.extraPaths": ["../common", "../vector-db"]
}
```

### 4. Workspace Configuration
The VS Code workspace (`briefly.code-workspace`) includes:
- Root directory (`.`) for running `tox` and accessing shared configurations
- Individual service directories for development

**Important**: `services/common` and `services/vector-db` are NOT included as separate workspace folders since they're shared libraries, not services. Including them would cause VS Code to expect them to have their own Python interpreters.

## Usage

After setup, you can import the packages in any service:

```python
# Import from common package
from common.telemetry import setup_telemetry, get_tracer, add_span_attributes

# Import from vector_db package
import vector_db
from vector_db.pinecone_client import PineconeClient
from vector_db.indexing_service import IndexingService
```

## Manual Installation (Per Service)

If you need to install manually for a specific service:

```bash
# The unified setup script handles this automatically
./setup-dev.sh
```

For manual installation (if needed):
```bash
cd services/{service-name}
source ../../venv/bin/activate  # Use unified venv
pip install -e ../common
pip install -e ../vector-db
```

## Verification

To verify the setup works:

1. Activate the unified virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Test imports:
   ```bash
   python -c "from common.telemetry import setup_telemetry; print('✓ Common working!')"
   python -c "import vector_db; print('✓ Vector DB working!')"
   ```

3. Check installed packages:
   ```bash
   pip list | grep -E "(common|vector-db)"
   ```

## Services Configured

- ✅ office_service
- ✅ chat_service
- ✅ user_management

## Files Created/Modified

- `services/common/setup.py` (new)
- `services/vector-db/setup.py` (new)
- `services/vector-db/__init__.py` (new)
- `services/office_service/.vscode/settings.json` (updated)
- `services/chat_service/.vscode/settings.json` (updated)
- `services/user_management/.vscode/settings.json` (updated)
- `setup-dev.sh` (updated - now includes shared package installation)
- `briefly.code-workspace` (updated - removed vector-db folder, added root)

## Technical Details

The setup uses:
- **Editable installs** (`pip install -e`): Links to source directories rather than copying files
- **Explicit package configuration**: Uses `packages=["package_name"]` and `package_dir` for precise control
- **VS Code extra paths**: Enables IntelliSense for the shared packages

This approach follows Python packaging best practices while maintaining the flexibility needed for active development.
