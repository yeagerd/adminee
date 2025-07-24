import os
import time
import logging
import json

from microsoft_graph_client import MicrosoftGraphClient
from pubsub_client import publish_message

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST")
MICROSOFT_TOPIC = "microsoft-notifications"
MICROSOFT_SUBSCRIPTION = os.getenv("MICROSOFT_SUBSCRIPTION", "microsoft-notifications-sub")

EMAIL_PROCESSING_TOPIC = "email-processing"

logging.basicConfig(level=logging.INFO)

def process_microsoft_notification(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        logging.info(f"Processing Microsoft notification: {data}")
        # TODO: Retrieve access token for the user (mocked for now)
        access_token = os.getenv("MS_GRAPH_ACCESS_TOKEN", "test-access-token")
        graph_client = MicrosoftGraphClient(access_token)
        # Fetch emails using notification
        emails = graph_client.fetch_emails_from_notification(data)
        logging.info(f"Fetched {len(emails)} emails from Microsoft Graph")
        # Publish each email to email-processing topic with retry
        for email in emails:
            backoff = 1
            for attempt in range(5):
                try:
                    publish_message(EMAIL_PROCESSING_TOPIC, email)
                    break
                except Exception as e:
                    logging.error(f"Failed to publish email to pubsub: {e}, retrying in {backoff}s")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
            else:
                logging.error(f"ALERT: Failed to publish email after retries. Email: {email}")
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