#!/usr/bin/env python3
"""
Migration script for Pub/Sub topics from old naming to new data-type focused naming.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.demos.settings_demos import get_demo_settings


def migrate_pubsub_topics() -> None:
    """Migrate Pub/Sub topics from old naming to new data-type focused naming"""
    settings = get_demo_settings()

    print("Migrating Pub/Sub topics to new data-type focused naming...")
    print(f"Project ID: {settings.pubsub_project_id}")
    print(f"Emulator Host: {settings.pubsub_emulator_host}")

    # Set environment variable for Pub/Sub emulator
    os.environ["PUBSUB_EMULATOR_HOST"] = settings.pubsub_emulator_host

    # Topic mapping: old_name -> new_name
    topic_migrations = {
        "email-backfill": "emails",
        "calendar-updates": "calendars",
        "contact-updates": "contacts",
    }

    print("\nTopic migration plan:")
    for old_topic, new_topic in topic_migrations.items():
        print(f"  {old_topic} -> {new_topic}")

    print("\nNote: This migration script will:")
    print("1. Create new topics with new names")
    print("2. Keep old topics for backward compatibility")
    print("3. You can manually delete old topics after confirming new ones work")

    # Create new topics
    print("\nCreating new topics...")
    for old_topic, new_topic in topic_migrations.items():
        topic_name = f"projects/{settings.pubsub_project_id}/topics/{new_topic}"
        print(f"\nCreating new topic: {new_topic}")

        try:
            # Create topic using gcloud CLI
            result = subprocess.run(
                [
                    "gcloud",
                    "pubsub",
                    "topics",
                    "create",
                    topic_name,
                    "--project",
                    settings.pubsub_project_id,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            print(f"✅ Created new topic: {new_topic}")

        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr:
                print(f"✅ New topic already exists: {new_topic}")
            else:
                print(f"❌ Failed to create new topic {new_topic}: {e.stderr}")

        except FileNotFoundError:
            print(f"❌ gcloud CLI not found. Please install Google Cloud SDK.")
            print(f"   Or create topics manually in the Pub/Sub emulator.")
            break

    # Create additional new topics that don't have old equivalents
    additional_topics = [
        "word_documents",
        "word_fragments",
        "sheet_documents",
        "sheet_fragments",
        "presentation_documents",
        "presentation_fragments",
        "task_documents",
        "todos",
        "llm_chats",
        "shipment_events",
        "meeting_polls",
        "bookings",
    ]

    print("\nCreating additional new topics...")
    for topic in additional_topics:
        topic_name = f"projects/{settings.pubsub_project_id}/topics/{topic}"
        print(f"\nCreating topic: {topic}")

        try:
            # Create topic using gcloud CLI
            result = subprocess.run(
                [
                    "gcloud",
                    "pubsub",
                    "topics",
                    "create",
                    topic_name,
                    "--project",
                    settings.pubsub_project_id,
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            print(f"✅ Created topic: {topic}")

        except subprocess.CalledProcessError as e:
            if "already exists" in e.stderr:
                print(f"✅ Topic already exists: {topic}")
            else:
                print(f"❌ Failed to create topic {topic}: {e.stderr}")

        except FileNotFoundError:
            print(f"❌ gcloud CLI not found. Please install Google Cloud SDK.")
            print(f"   Or create topics manually in the Pub/Sub emulator.")
            break

    print("\nTopic migration completed!")
    print("\nNext steps:")
    print("1. Update your services to publish to new topic names")
    print("2. Update your consumers to subscribe to new topic names")
    print("3. Test that new topics work correctly")
    print("4. After confirming everything works, you can manually delete old topics")
    print("\nOld topics to delete (after testing):")
    for old_topic in topic_migrations.keys():
        print(f"  - {old_topic}")


if __name__ == "__main__":
    migrate_pubsub_topics()
