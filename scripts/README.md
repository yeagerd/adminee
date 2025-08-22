# Scripts Directory

This directory contains utility scripts for managing the Briefly platform.

## PubSub Management Scripts

### Local Development: `pubsub-manager.sh`

A unified script for managing the local Pub/Sub emulator during development.

**Features:**
- Start/stop/cleanup Pub/Sub emulator container
- Create topics and subscriptions automatically
- Health checking and status reporting
- REST API integration (no gcloud authentication required)
- Comprehensive topic and subscription listing
- Automatic Docker container management

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

**Implementation Details:**
- Uses Docker container with Google Cloud CLI image
- REST API endpoints for topic/subscription management
- Automatic health checking and container lifecycle management
- JSON parsing with jq for reliable data extraction

**Prerequisites:**
- Docker running
- jq (for JSON parsing) - usually pre-installed on macOS/Linux

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

## Recent Improvements

**Version 2.0 Changes** (Current):
- ✅ **REST API Integration**: Replaced gcloud commands with direct REST API calls
- ✅ **No Authentication Required**: Works seamlessly with local emulator
- ✅ **Improved JSON Parsing**: Uses jq for reliable topic/subscription listing
- ✅ **Better Error Handling**: Clear error messages and graceful fallbacks
- ✅ **Comprehensive Status**: Shows all topics and subscriptions clearly

**Previous Version Issues Resolved**:
- ❌ "Could not list topics/subscriptions" errors
- ❌ gcloud authentication requirements
- ❌ Unreliable JSON parsing with grep/sed

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

## Troubleshooting

### Common Issues

**"Could not list topics/subscriptions"**:
- This was a previous issue with gcloud authentication
- Now resolved with REST API integration
- Ensure emulator is running: `./scripts/pubsub-manager.sh status`

**Port conflicts**:
- Default port is 8085
- Check if port is available: `lsof -i :8085`
- Use `./scripts/pubsub-manager.sh cleanup` to remove container

**Container issues**:
- If container is in bad state: `./scripts/pubsub-manager.sh cleanup`
- Then restart: `./scripts/pubsub-manager.sh start`

**Missing jq**:
- Install jq: `brew install jq` (macOS) or `apt-get install jq` (Ubuntu)
- Script will fall back to grep/sed if jq unavailable

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
