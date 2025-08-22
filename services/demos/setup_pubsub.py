#!/usr/bin/env python3
"""
Setup script for Pub/Sub topics required by the event-driven architecture.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.demos.settings_demos import get_demo_settings


def setup_pubsub_topics() -> None:
    """Set up Pub/Sub topics for the Vespa backfill demo"""
    settings = get_demo_settings()

    print("Setting up Pub/Sub topics for event-driven architecture...")
    print(f"Project ID: {settings.pubsub_project_id}")
    print(f"Emulator Host: {settings.pubsub_emulator_host}")

    # Set environment variable for Pub/Sub emulator
    os.environ["PUBSUB_EMULATOR_HOST"] = settings.pubsub_emulator_host

    # New data-type focused topics
    topics = [
        # Core data types
        "emails",  # Replaces "email-backfill"
        "calendars",  # Replaces "calendar-updates"
        "contacts",  # Replaces "contact-updates"
        
        # Office document types
        "word_documents",
        "word_fragments",
        "sheet_documents",
        "sheet_fragments",
        "presentation_documents",
        "presentation_fragments",
        "task_documents",
        
        # Todo types
        "todos",
        
        # Internal tool types
        "llm_chats",
        "shipment_events",
        "meeting_polls",
        "bookings",
    ]

    for topic in topics:
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

    print("\nPub/Sub setup completed!")
    print("\nNote: If you don't have gcloud CLI installed, you can:")
    print("1. Install Google Cloud SDK, or")
    print("2. Create topics manually in the Pub/Sub emulator UI, or")
    print("3. Use the Pub/Sub emulator's REST API directly")


if __name__ == "__main__":
    setup_pubsub_topics()
