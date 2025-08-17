#!/usr/bin/env python3
"""
Simple Pub/Sub topic setup using the emulator's REST API.
"""

import json

import requests


def create_pubsub_topic(
    project_id: str, topic_name: str, emulator_host: str = "localhost:8085"
):
    """Create a Pub/Sub topic using the emulator's REST API"""

    url = f"http://{emulator_host}/v1/projects/{project_id}/topics"
    data = {"name": f"projects/{project_id}/topics/{topic_name}"}

    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"✅ Created topic: {topic_name}")
            return True
        elif response.status_code == 409:  # Already exists
            print(f"✅ Topic already exists: {topic_name}")
            return True
        else:
            print(
                f"❌ Failed to create topic {topic_name}: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        print(f"❌ Error creating topic {topic_name}: {e}")
        return False


def main():
    """Set up required Pub/Sub topics"""
    project_id = "briefly-dev"
    emulator_host = "localhost:8085"

    print("Setting up Pub/Sub topics for Vespa backfill demo...")
    print(f"Project ID: {project_id}")
    print(f"Emulator Host: {emulator_host}")

    # Topics to create
    topics = [
        "email-backfill",  # Changed from "backfill-emails"
        "calendar-updates",  # Changed from "backfill-calendar"
        "contact-updates",  # Changed from "backfill-contacts"
    ]

    success_count = 0
    for topic in topics:
        if create_pubsub_topic(project_id, topic, emulator_host):
            success_count += 1

    print(f"\n✅ Successfully set up {success_count}/{len(topics)} topics!")

    if success_count == len(topics):
        print("🎉 All Pub/Sub topics are ready for the Vespa backfill demo!")
    else:
        print("⚠️  Some topics failed to create. Check the emulator status.")


if __name__ == "__main__":
    main()
