#!/usr/bin/env python3
"""
Script to inject realistic test data into local pubsub emulator.

This script publishes test webhook notifications and email data to the
local pubsub emulator to test the email_sync service pipeline end-to-end.

Usage:
    python scripts/inject_test_data.py [--gmail] [--microsoft] [--emails] [--all]
"""

import argparse
import json
import os
import sys
import time

# Add the parent directory to the path so we can import test_data
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_data import (
    get_all_amazon_emails,
    get_all_microsoft_emails,
    get_all_survey_emails,
    get_all_tracking_emails,
    gmail_webhook_payload,
    gmail_webhook_payload_with_multiple_emails,
    microsoft_webhook_payload,
    microsoft_webhook_payload_multiple_changes,
)

# Set up environment for local pubsub emulator
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"

try:
    from google.cloud import pubsub_v1
except ImportError:
    print(
        "Error: google-cloud-pubsub not installed. Install with: pip install google-cloud-pubsub"
    )
    sys.exit(1)


class TestDataInjector:
    """Class to inject test data into pubsub emulator."""

    def __init__(self, project_id: str = "test-project"):
        self.project_id = project_id
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

        # Define topic names
        self.topics = {
            "gmail_notifications": f"projects/{project_id}/topics/gmail-notifications",
            "microsoft_notifications": f"projects/{project_id}/topics/microsoft-notifications",
            "email_processing": f"projects/{project_id}/topics/email-processing",
            "package_tracker_events": f"projects/{project_id}/topics/package-tracker-events",
            "survey_events": f"projects/{project_id}/topics/survey-events",
            "amazon_events": f"projects/{project_id}/topics/amazon-events",
        }

        # Define subscription names
        self.subscriptions = {
            "gmail_notifications": f"projects/{project_id}/subscriptions/gmail-notifications-sub",
            "microsoft_notifications": f"projects/{project_id}/subscriptions/microsoft-notifications-sub",
            "email_processing": f"projects/{project_id}/subscriptions/email-processing-sub",
            "package_tracker_events": f"projects/{project_id}/subscriptions/package-tracker-events-sub",
            "survey_events": f"projects/{project_id}/subscriptions/survey-events-sub",
            "amazon_events": f"projects/{project_id}/subscriptions/amazon-events-sub",
        }

    def create_topics_and_subscriptions(self):
        """Create all required topics and subscriptions."""
        print("Creating topics and subscriptions...")

        for topic_name, topic_path in self.topics.items():
            try:
                self.publisher.create_topic(name=topic_path)
                print(f"✓ Created topic: {topic_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"✓ Topic already exists: {topic_name}")
                else:
                    print(f"✗ Failed to create topic {topic_name}: {e}")

        for sub_name, sub_path in self.subscriptions.items():
            try:
                # Get the corresponding topic path
                topic_key = sub_name.replace(
                    "_notifications", "_notifications"
                ).replace("_events", "_events")
                topic_path = self.topics.get(topic_key, self.topics["email_processing"])

                self.subscriber.create_subscription(name=sub_path, topic=topic_path)
                print(f"✓ Created subscription: {sub_name}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"✓ Subscription already exists: {sub_name}")
                else:
                    print(f"✗ Failed to create subscription {sub_name}: {e}")

    def publish_gmail_webhooks(self):
        """Publish Gmail webhook notifications."""
        print("\nPublishing Gmail webhook notifications...")

        webhook_payloads = [
            gmail_webhook_payload(),
            gmail_webhook_payload_with_multiple_emails(),
            gmail_webhook_payload(history_id="99999", email_address="test@example.com"),
        ]

        for i, payload in enumerate(webhook_payloads, 1):
            try:
                message_data = json.dumps(payload).encode("utf-8")
                future = self.publisher.publish(
                    self.topics["gmail_notifications"], data=message_data
                )
                message_id = future.result()
                print(f"✓ Published Gmail webhook {i}: {message_id}")
            except Exception as e:
                print(f"✗ Failed to publish Gmail webhook {i}: {e}")

    def publish_microsoft_webhooks(self):
        """Publish Microsoft webhook notifications."""
        print("\nPublishing Microsoft webhook notifications...")

        webhook_payloads = [
            microsoft_webhook_payload(),
            microsoft_webhook_payload_multiple_changes(),
            microsoft_webhook_payload(change_type="updated", resource="me/messages/2"),
        ]

        for i, payload in enumerate(webhook_payloads, 1):
            try:
                message_data = json.dumps(payload).encode("utf-8")
                future = self.publisher.publish(
                    self.topics["microsoft_notifications"], data=message_data
                )
                message_id = future.result()
                print(f"✓ Published Microsoft webhook {i}: {message_id}")
            except Exception as e:
                print(f"✗ Failed to publish Microsoft webhook {i}: {e}")

    def publish_email_data(self):
        """Publish email data to email-processing topic."""
        print("\nPublishing email data to email-processing topic...")

        # Get all test emails
        all_emails = (
            get_all_tracking_emails()
            + get_all_amazon_emails()
            + get_all_survey_emails()
            + get_all_microsoft_emails()
        )

        for i, email in enumerate(all_emails, 1):
            try:
                # Convert email to the format expected by the parser
                if "payload" in email and "body" in email["payload"]:
                    # Gmail format
                    email_data = {
                        "from": email["payload"]["headers"][1]["value"],  # From header
                        "body": email["payload"]["body"]["data"],
                    }
                elif "body" in email and "content" in email["body"]:
                    # Microsoft format
                    email_data = {
                        "from": email["from"]["emailAddress"]["address"],
                        "body": email["body"]["content"],
                    }
                else:
                    # Fallback
                    email_data = {"from": "test@example.com", "body": "Test email body"}

                message_data = json.dumps(email_data).encode("utf-8")
                future = self.publisher.publish(
                    self.topics["email_processing"], data=message_data
                )
                message_id = future.result()
                print(f"✓ Published email {i}: {message_id}")

                # Small delay to avoid overwhelming the system
                time.sleep(0.1)

            except Exception as e:
                print(f"✗ Failed to publish email {i}: {e}")

    def listen_for_events(self, duration: int = 30):
        """Listen for events on downstream topics."""
        print(f"\nListening for events for {duration} seconds...")

        received_events = {
            "package_tracker_events": [],
            "survey_events": [],
            "amazon_events": [],
        }

        def callback(message):
            """Callback for received messages."""
            try:
                data = json.loads(message.data.decode("utf-8"))
                topic_name = message.attributes.get("topic", "unknown")

                if "package-tracker-events" in topic_name:
                    received_events["package_tracker_events"].append(data)
                    print(
                        f"📦 Package event: {data.get('carrier', 'Unknown')} - {data.get('tracking_number', 'No tracking')}"
                    )
                elif "survey-events" in topic_name:
                    received_events["survey_events"].append(data)
                    print(f"📊 Survey event: {data.get('survey_url', 'No URL')}")
                elif "amazon-events" in topic_name:
                    received_events["amazon_events"].append(data)
                    print(f"📦 Amazon event: {data.get('status', 'No status')}")

                message.ack()
            except Exception as e:
                print(f"Error processing message: {e}")
                message.nack()

        # Start listening on all event topics
        streaming_pulls = []
        for sub_name, sub_path in self.subscriptions.items():
            if "events" in sub_name:
                try:
                    streaming_pull_future = self.subscriber.subscribe(
                        sub_path, callback=callback
                    )
                    streaming_pulls.append(streaming_pull_future)
                    print(f"✓ Listening on {sub_name}")
                except Exception as e:
                    print(f"✗ Failed to listen on {sub_name}: {e}")

        # Wait for the specified duration
        time.sleep(duration)

        # Cancel streaming pulls
        for streaming_pull_future in streaming_pulls:
            streaming_pull_future.cancel()

        # Print summary
        print("\n📊 Event Summary:")
        print(f"  Package events: {len(received_events['package_tracker_events'])}")
        print(f"  Survey events: {len(received_events['survey_events'])}")
        print(f"  Amazon events: {len(received_events['amazon_events'])}")

        return received_events


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Inject test data into pubsub emulator"
    )
    parser.add_argument(
        "--gmail", action="store_true", help="Publish Gmail webhook notifications"
    )
    parser.add_argument(
        "--microsoft",
        action="store_true",
        help="Publish Microsoft webhook notifications",
    )
    parser.add_argument("--emails", action="store_true", help="Publish email data")
    parser.add_argument(
        "--listen", type=int, default=0, help="Listen for events for N seconds"
    )
    parser.add_argument("--all", action="store_true", help="Publish all test data")
    parser.add_argument(
        "--setup", action="store_true", help="Create topics and subscriptions"
    )

    args = parser.parse_args()

    # If no specific options provided, default to --all
    if not any([args.gmail, args.microsoft, args.emails, args.setup, args.listen]):
        args.all = True

    try:
        injector = TestDataInjector()

        if args.setup or args.all:
            injector.create_topics_and_subscriptions()

        if args.gmail or args.all:
            injector.publish_gmail_webhooks()

        if args.microsoft or args.all:
            injector.publish_microsoft_webhooks()

        if args.emails or args.all:
            injector.publish_email_data()

        if args.listen > 0:
            injector.listen_for_events(args.listen)

        print("\n✅ Test data injection completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure the pubsub emulator is running:")
        print("  gcloud beta emulators pubsub start --project=test-project")
        sys.exit(1)


if __name__ == "__main__":
    main()
