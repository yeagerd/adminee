#!/usr/bin/env python3
"""
Setup script for Pub/Sub topics required by the Vespa backfill demo.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add the services directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# from services.demos.settings_demos import get_demo_settings  # Removed to prevent import-time errors


def setup_pubsub_topics() -> None:
    """Set up Pub/Sub topics for the Vespa backfill demo"""
    from services.demos.settings_demos import get_demo_settings  # Lazy import

    settings = get_demo_settings()

    print("Setting up Pub/Sub topics for Vespa backfill demo...")
    print(f"Project ID: {settings.pubsub_project_id}")
    print(f"Emulator Host: {settings.pubsub_emulator_host}")

    # Set environment variable for Pub/Sub emulator
    os.environ["PUBSUB_EMULATOR_HOST"] = settings.pubsub_emulator_host

    # Topics to create
    topics = [
        "email-backfill",  # Changed from "backfill-emails"
        "calendar-updates",  # Changed from "backfill-calendar"
        "contact-updates",  # Changed from "backfill-contacts"
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
