# Shared Packages Setup for Briefly Services

This document explains the setup for shared `common` and `vector_db` packages across all services in the Briefly project.

## Overview

The setup provides:
- **Editable installs**: Changes to shared packages are immediately available to all services
- **Proper import resolution**: Standard Python import syntax works across services
- **VS Code IntelliSense**: Enhanced code completion and go-to-definition
- **Type checking**: mypy properly resolves imports from shared packages

## Quick Setup

Run the installation script from the repository root:

```bash
./install_common_packages.sh
```

This installs both packages in editable mode for all services with virtual environments.

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
cd services/{service-name}
source venv/bin/activate
pip install -e ../common
pip install -e ../vector-db
deactivate
```

Example for office_service:
```bash
cd services/office_service
source venv/bin/activate
pip install -e ../common
pip install -e ../vector-db
deactivate
```

## Verification

To verify the setup works:

1. Activate any service's virtual environment:
   ```bash
   cd services/office_service
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
- `install_common_packages.sh` (new)

## Technical Details

The setup uses:
- **Editable installs** (`pip install -e`): Links to source directories rather than copying files
- **Explicit package configuration**: Uses `packages=["package_name"]` and `package_dir` for precise control
- **VS Code extra paths**: Enables IntelliSense for the shared packages

This approach follows Python packaging best practices while maintaining the flexibility needed for active development. 