import json
import os
from typing import Any

from google.cloud import pubsub_v1  # type: ignore[attr-defined]

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST")


def publish_message(topic: str, message: Any) -> None:
    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    publisher = pubsub_v1.PublisherClient()
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set.")
    topic_path = publisher.topic_path(project_id, topic)
    publisher.publish(topic_path, data=json.dumps(message).encode("utf-8"))
