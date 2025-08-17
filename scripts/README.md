# Scripts Directory

This directory contains various utility scripts for managing the Briefly project.

## Vespa Management

The main script for managing Vespa services is `vespa.sh`. This script consolidates the functionality that was previously spread across three separate scripts:

- ~~`deploy-vespa.sh`~~ (removed)
- ~~`local_vespa.sh`~~ (removed)  
- ~~`start-vespa-local.sh`~~ (removed)

### Usage

```bash
# Check status and start services if needed (default behavior)
./scripts/vespa.sh

# Start all Vespa services (container + Python services)
./scripts/vespa.sh --start

# Deploy the Briefly application to Vespa
./scripts/vespa.sh --deploy

# Stop all Vespa services
./scripts/vespa.sh --stop

# Stop and remove the Vespa container
./scripts/vespa.sh --cleanup

# Restart all Vespa services
./scripts/vespa.sh --restart

# Show current status
./scripts/vespa.sh --status

# Show help
./scripts/vespa.sh --help
```

### What it manages

The consolidated script manages:

1. **Vespa Container**: Docker container running Vespa engine
2. **Briefly Application**: Deploys your Vespa configuration from `vespa/` directory
3. **Python Services**: 
   - Vespa Loader Service (port 9001)
   - Vespa Query Service (port 9002)

### Key Features

- **Automatic Health Checks**: Monitors all services and starts them if needed
- **Briefly Configuration**: Properly deploys your `vespa/services.xml`, `vespa/hosts.xml`, and `vespa/schemas/` configuration
- **Real-time Logging**: Shows deployment progress with live log monitoring
- **Error Handling**: Comprehensive error checking and user-friendly messages
- **Service Management**: Start, stop, restart, and cleanup operations

### Configuration Files

The script expects your Vespa configuration in the `vespa/` directory:

- `vespa/services.xml` - Service definitions
- `vespa/hosts.xml` - Host configuration  
- `vespa/schemas/briefly_document.sd` - Document schema

### Endpoints

Once deployed, your Briefly application will be available at:

- **Search**: http://localhost:8080/search/
- **Documents**: http://localhost:8080/document/v1/briefly/briefly_document/
- **Status**: http://localhost:8080/application/v2/status

### Testing

After deployment, you can test the chat demo:

```bash
python services/demos/vespa_chat.py
```

## Other Scripts

- `start-all-services.sh` - Starts all project services
- `postgres-*.sh` - PostgreSQL database management
- `run-migrations.sh` - Database migration runner
- `setup-*.sh` - Various setup and configuration scripts
