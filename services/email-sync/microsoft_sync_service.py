import os
import time
import logging
import json

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST")
MICROSOFT_TOPIC = "microsoft-notifications"
MICROSOFT_SUBSCRIPTION = os.getenv("MICROSOFT_SUBSCRIPTION", "microsoft-notifications-sub")

logging.basicConfig(level=logging.INFO)

def process_microsoft_notification(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        logging.info(f"Processing Microsoft notification: {data}")
        # TODO: Fetch emails using Microsoft Graph API
        # TODO: Publish each email to email-processing topic
        message.ack()
    except Exception as e:
        logging.error(f"Failed to process message: {e}")
        message.nack()

def run():
    from google.cloud import pubsub_v1
    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, MICROSOFT_SUBSCRIPTION)
    backoff = 1
    while True:
        try:
            streaming_pull_future = subscriber.subscribe(
                subscription_path, callback=process_microsoft_notification
            )
            logging.info(f"Listening for messages on {subscription_path}...")
            streaming_pull_future.result()
        except Exception as e:
            logging.error(f"Subscriber error: {e}, retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)

if __name__ == "__main__":
    run() 