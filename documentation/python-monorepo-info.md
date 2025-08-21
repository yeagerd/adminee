# Shared Packages Setup for Briefly Services

This document explains the setup for shared `common` package across all services in the Briefly project.

## Overview

The setup provides:
- **Editable installs**: Changes to shared packages are immediately available to all services
- **Proper import resolution**: Standard Python import syntax works across services
- **VS Code IntelliSense**: Enhanced code completion and go-to-definition
- **Type checking**: mypy properly resolves imports from shared packages

## Quick Setup

Run the installation setup script from the repository root:

```bash
./install.sh
```

This script will:
- Create virtual environments for the main project and all services
- Install requirements for each service
- Install shared packages in editable mode for all services

## What Was Configured

### 1. Package Structure
- `services/common/`: Contains telemetry and shared utilities


### 2. Setup Files Created
- `services/common/setup.py`: Makes common installable as a package


### 3. VS Code Configuration
Each service's `.vscode/settings.json` includes:
```json
{
  "python.defaultInterpreterPath": "venv/bin/python",
  "python.analysis.extraPaths": ["../common"]
}
```

### 4. Workspace Configuration
The VS Code workspace (`briefly.code-workspace`) includes:
- Root directory (`.`) for running `tox` and accessing shared configurations
- Individual service directories for development

**Important**: `services/common` is NOT included as a separate workspace folder since it's a shared library, not a service. Including it would cause VS Code to expect it to have its own Python interpreter.

## Usage

After setup, you can import the packages in any service:

```python
# Import from common package
from common.telemetry import setup_telemetry, get_tracer, add_span_attributes


```

## Manual Installation (Per Service)

If you need to install manually for a specific service:

```bash
# The unified setup script handles this automatically
./install.sh
```

For manual installation (if needed):
```bash
cd services/{service-name}
source ../../venv/bin/activate  # Use unified venv
pip install -e ../common

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
   
   ```

3. Check installed packages:
   ```bash
   pip list | grep -E "(common)"
   ```

## Services Configured

- ✅ office_service
- ✅ chat_service
- ✅ user_management

## Files Created/Modified

- `services/common/setup.py` (new)

- `services/office/.vscode/settings.json` (updated)
- `services/chat/.vscode/settings.json` (updated)
- `services/user/.vscode/settings.json` (updated)
- `install.sh` (updated - now includes shared package installation)
- `briefly.code-workspace` (updated - removed vector-db folder, added root)

## Technical Details

The setup uses:
- **Editable installs** (`pip install -e`): Links to source directories rather than copying files
- **Explicit package configuration**: Uses `packages=["package_name"]` and `package_dir` for precise control
- **VS Code extra paths**: Enables IntelliSense for the shared packages

This approach follows Python packaging best practices while maintaining the flexibility needed for active development.
