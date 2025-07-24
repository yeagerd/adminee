import os
import json
from google.cloud import pubsub_v1

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST")

def publish_message(topic_name, data):
    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, topic_name)
    if isinstance(data, dict):
        data = json.dumps(data).encode("utf-8")
    elif isinstance(data, str):
        data = data.encode("utf-8")
    future = publisher.publish(topic_path, data)
    return future 