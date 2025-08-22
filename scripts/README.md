# Scripts Directory

This directory contains utility scripts for managing the Briefly platform.

## Vespa Management Scripts

### Vespa Management: `vespa.sh`

A unified script for managing the Vespa search engine container and deploying the Briefly application.

**Features:**
- Start/stop/restart Vespa container
- Deploy Briefly application to Vespa
- Health checking and status reporting
- Data clearing operations
- **Single invocation** - automatically starts container and deploys app if needed

**Usage:**
```bash
# Start container, deploy app, and show status (default - recommended)
./scripts/vespa.sh

# Same as above (explicit auto mode)
./scripts/vespa.sh --auto

# Start Vespa container only
./scripts/vespa.sh --start

# Deploy Briefly application only
./scripts/vespa.sh --deploy

# Show current status
./scripts/vespa.sh --status

# Stop Vespa container
./scripts/vespa.sh --stop

# Restart Vespa container
./scripts/vespa.sh --restart

# Clean up container
./scripts/vespa.sh --cleanup

# Clear data for specific user
./scripts/vespa.sh --clear-data --email {email} --env-file {env_file} [--force]

# Clear all data for all users
./scripts/vespa.sh --clear-data-all-users

# Show help
./scripts/vespa.sh --help
```

**Key Benefits:**
- 🚀 **Single command setup** - No more separate `--start` and `--deploy` calls
- 🔍 **Smart health checks** - Automatically detects what needs to be done
- 📦 **Automatic deployment** - Deploys Briefly app if not already deployed
- 📊 **Comprehensive status** - Shows container and application status

**Prerequisites:**
- Docker running
- Vespa configuration files in `vespa/` directory

## PubSub Management Scripts

### Local Development: `pubsub-manager.sh`

A unified script for managing the local Pub/Sub emulator during development.

**Features:**
- Start/stop/cleanup Pub/Sub emulator container
- Create topics and subscriptions automatically
- Health checking and status reporting
- Fallback to REST API if gcloud CLI unavailable

**Usage:**
```bash
# Start emulator and setup everything (default)
./scripts/pubsub-manager.sh

# Start emulator and setup topics/subscriptions
./scripts/pubsub-manager.sh start

# Setup topics/subscriptions only (emulator must be running)
./scripts/pubsub-manager.sh setup

# Show current status
./scripts/pubsub-manager.sh status

# Stop emulator
./scripts/pubsub-manager.sh stop

# Remove emulator container
./scripts/pubsub-manager.sh cleanup

# Show help
./scripts/pubsub-manager.sh --help
```

**Environment Variables:**
- `PUBSUB_PROJECT_ID` - Project ID (default: briefly-dev)
- `PUBSUB_EMULATOR_HOST` - Emulator host (default: localhost:8085)

**Prerequisites:**
- Docker running
- Optional: gcloud CLI for enhanced functionality

### Production GCP: `gcp-pubsub-setup.sh`

A script for setting up Pub/Sub infrastructure in Google Cloud Platform.

**Features:**
- Create topics and subscriptions in GCP
- Cleanup infrastructure when needed
- List existing resources
- GCP authentication and permission checks

**Usage:**
```bash
# Create all topics and subscriptions
./scripts/gcp-pubsub-setup.sh create

# List all resources
./scripts/gcp-pubsub-setup.sh list

# Cleanup all resources (with confirmation)
./scripts/gcp-pubsub-setup.sh cleanup

# Show help
./scripts/gcp-pubsub-setup.sh --help
```

**Environment Variables:**
- `GOOGLE_CLOUD_PROJECT_ID` - GCP Project ID (default: briefly-prod)

**Prerequisites:**
- gcloud CLI installed and authenticated
- Appropriate permissions on the GCP project

## Topics and Subscriptions

Both scripts create the following infrastructure:

### Topics
- `email-backfill` - For email backfill operations
- `calendar-updates` - For calendar update notifications
- `contact-updates` - For contact update notifications

### Subscriptions

**Router Subscriptions:**
- `email-router-subscription` → `email-backfill`
- `calendar-router-subscription` → `calendar-updates`
- `contact-router-subscription` → `contact-updates`

**Vespa Loader Subscriptions:**
- `vespa-loader-email-backfill` → `email-backfill`
- `vespa-loader-calendar-updates` → `calendar-updates`
- `vespa-loader-contact-updates` → `contact-updates`

## Migration from Old Scripts

The following scripts have been consolidated and removed:
- `start-pubsub-emulator.sh` → `pubsub-manager.sh`
- `local-pubsub.sh` → `pubsub-manager.sh`
- `create_pubsub_topics.py` → `pubsub-manager.sh`
- `setup-pubsub-topics.sh` → `gcp-pubsub-setup.sh`
- `fix-pubsub-topics.sh` → `gcp-pubsub-setup.sh`
- `create-vespa-subscriptions.sh` → `pubsub-manager.sh`

## Quick Start for Development

1. **Start the emulator:**
   ```bash
   ./scripts/pubsub-manager.sh start
   ```

2. **Verify it's running:**
   ```bash
   ./scripts/pubsub-manager.sh status
   ```

3. **Stop when done:**
   ```bash
   ./scripts/pubsub-manager.sh stop
   ```

## Quick Start for Production

1. **Set your GCP project:**
   ```bash
   export GOOGLE_CLOUD_PROJECT_ID=your-project-id
   ```

2. **Create infrastructure:**
   ```bash
   ./scripts/gcp-pubsub-setup.sh create
   ```

3. **Verify setup:**
   ```bash
   ./scripts/gcp-pubsub-setup.sh list
   ```
