#!/bin/bash

# Create vespa-loader subscriptions using Pub/Sub emulator REST API
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

echo "Creating vespa-loader subscriptions..."
echo "Project ID: $PUBSUB_PROJECT_ID"
echo "Emulator Host: $PUBSUB_EMULATOR_HOST"

# Create vespa-loader subscriptions using REST API
echo "Creating vespa-loader-email-backfill subscription..."
curl -s -X POST -H 'Content-Type: application/json' \
  "http://$PUBSUB_EMULATOR_HOST/v1/projects/$PUBSUB_PROJECT_ID/subscriptions" \
  -d "{
    \"name\": \"projects/$PUBSUB_PROJECT_ID/subscriptions/vespa-loader-email-backfill\",
    \"topic\": \"projects/$PUBSUB_PROJECT_ID/topics/email-backfill\"
  }" || echo "Subscription may already exist"

echo "Creating vespa-loader-calendar-updates subscription..."
curl -s -X POST -H 'Content-Type: application/json' \
  "http://$PUBSUB_EMULATOR_HOST/v1/projects/$PUBSUB_PROJECT_ID/subscriptions" \
  -d "{
    \"name\": \"projects/$PUBSUB_PROJECT_ID/subscriptions/vespa-loader-calendar-updates\",
    \"topic\": \"projects/$PUBSUB_PROJECT_ID/topics/calendar-updates\"
  }" || echo "Subscription may already exist"

echo "Creating vespa-loader-contact-updates subscription..."
curl -s -X POST -H 'Content-Type: application/json' \
  "http://$PUBSUB_EMULATOR_HOST/v1/projects/$PUBSUB_PROJECT_ID/subscriptions" \
  -d "{
    \"name\": \"projects/$PUBSUB_PROJECT_ID/subscriptions/vespa-loader-contact-updates\",
    \"topic\": \"projects/$PUBSUB_PROJECT_ID/topics/contact-updates\"
  }" || echo "Subscription may already exist"

# List all subscriptions
echo ""
echo "All subscriptions:"
curl -s "http://$PUBSUB_EMULATOR_HOST/v1/projects/$PUBSUB_PROJECT_ID/subscriptions" | jq '.subscriptions[].name' 2>/dev/null || echo "Could not parse subscriptions (jq not available)"

echo ""
echo "✅ Vespa-loader subscriptions created successfully!"
echo "The vespa-loader service should now be able to consume messages."
