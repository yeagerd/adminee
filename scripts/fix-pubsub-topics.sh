#!/bin/bash

# Fix Pub/Sub topics script - creates the correct topic names
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

echo "Fixing Pub/Sub topics with correct names..."
echo "Project ID: $PUBSUB_PROJECT_ID"
echo "Emulator Host: $PUBSUB_EMULATOR_HOST"

# Delete old topics if they exist
echo "Cleaning up old topics..."
old_topics=("backfill-emails" "backfill-calendar" "backfill-contacts")
for topic in "${old_topics[@]}"; do
    if gcloud pubsub topics list --project=$PUBSUB_PROJECT_ID | grep -q "$topic"; then
        echo "Deleting old topic: $topic"
        gcloud pubsub topics delete "$topic" --project=$PUBSUB_PROJECT_ID --quiet || true
    fi
done

# Create correct topics
echo "Creating correct topics..."
correct_topics=("email-backfill" "calendar-updates" "contact-updates")
for topic in "${correct_topics[@]}"; do
    echo "Creating topic: $topic"
    gcloud pubsub topics create "$topic" --project=$PUBSUB_PROJECT_ID --quiet || echo "Topic $topic may already exist"
done

# Create subscriptions
echo "Creating subscriptions..."
gcloud pubsub subscriptions create email-router-subscription \
    --topic=email-backfill \
    --project=$PUBSUB_PROJECT_ID \
    --quiet || echo "Subscription may already exist"

gcloud pubsub subscriptions create calendar-router-subscription \
    --topic=calendar-updates \
    --project=$PUBSUB_PROJECT_ID \
    --quiet || echo "Subscription may already exist"

gcloud pubsub subscriptions create contact-router-subscription \
    --topic=contact-updates \
    --project=$PUBSUB_PROJECT_ID \
    --quiet || echo "Subscription may already exist"

# List all topics and subscriptions
echo ""
echo "Topics created:"
gcloud pubsub topics list --project=$PUBSUB_PROJECT_ID

echo ""
echo "Subscriptions created:"
gcloud pubsub subscriptions list --project=$PUBSUB_PROJECT_ID

echo ""
echo "✅ Pub/Sub topics fixed successfully!"
echo "The chat service should now be able to publish emails without 404 errors."
