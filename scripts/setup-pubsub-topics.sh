#!/bin/bash

# Set up Google Cloud Pubsub topics and subscriptions for the office router
set -e

# Check if environment variables are set
if [ -z "$PUBSUB_EMULATOR_HOST" ]; then
    echo "Error: PUBSUB_EMULATOR_HOST environment variable not set"
    echo "Please run: export PUBSUB_EMULATOR_HOST=localhost:8085"
    exit 1
fi

if [ -z "$PUBSUB_PROJECT_ID" ]; then
    echo "Error: PUBSUB_PROJECT_ID environment variable not set"
    echo "Please run: export PUBSUB_PROJECT_ID=briefly-dev"
    exit 1
fi

echo "Setting up PubSub topics and subscriptions..."
echo "Project ID: $PUBSUB_PROJECT_ID"
echo "Emulator Host: $PUBSUB_EMULATOR_HOST"

# Create topics
echo "Creating topics..."

# Email backfill topic
echo "Creating email-backfill topic..."
gcloud pubsub topics create email-backfill \
    --project=$PUBSUB_PROJECT_ID \
    --quiet

# Email updates topic
echo "Creating email-updates topic..."
gcloud pubsub topics create email-updates \
    --project=$PUBSUB_PROJECT_ID \
    --quiet

# Calendar updates topic
echo "Creating calendar-updates topic..."
gcloud pubsub topics create calendar-updates \
    --project=$PUBSUB_PROJECT_ID \
    --quiet

# Create subscriptions
echo "Creating subscriptions..."

# Email router subscription
echo "Creating email-router-subscription..."
gcloud pubsub subscriptions create email-router-subscription \
    --topic=email-backfill \
    --project=$PUBSUB_PROJECT_ID \
    --quiet

# Calendar router subscription
echo "Creating calendar-router-subscription..."
gcloud pubsub subscriptions create calendar-router-subscription \
    --topic=calendar-updates \
    --project=$PUBSUB_PROJECT_ID \
    --quiet

# List all topics and subscriptions
echo ""
echo "Topics created:"
gcloud pubsub topics list --project=$PUBSUB_PROJECT_ID

echo ""
echo "Subscriptions created:"
gcloud pubsub subscriptions list --project=$PUBSUB_PROJECT_ID

echo ""
echo "PubSub setup complete!"
echo "Topics and subscriptions are ready for the office router service."
