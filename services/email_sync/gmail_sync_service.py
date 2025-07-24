import json
import logging
import os
import time
from typing import Any

from services.email_sync.gmail_api_client import GmailAPIClient
from services.email_sync.pubsub_client import publish_message
from services.email_sync.schemas import GmailNotification

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST")
GMAIL_TOPIC = "gmail-notifications"
GMAIL_SUBSCRIPTION = os.getenv("GMAIL_SUBSCRIPTION", "gmail-notifications-sub")

EMAIL_PROCESSING_TOPIC = "email-processing"

logging.basicConfig(level=logging.INFO)


def process_gmail_notification(message: Any) -> None:
    try:
        data = json.loads(message.data.decode("utf-8"))
        notification = GmailNotification(**data)
        logging.info(f"Processing Gmail notification: {notification}")
        # TODO: Retrieve tokens and client info for the user (mocked for now)
        access_token = os.getenv("GMAIL_ACCESS_TOKEN", "test-access-token")
        refresh_token = os.getenv("GMAIL_REFRESH_TOKEN", "test-refresh-token")
        client_id = os.getenv("GMAIL_CLIENT_ID", "test-client-id")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET", "test-client-secret")
        token_uri = os.getenv("GMAIL_TOKEN_URI", "https://oauth2.googleapis.com/token")
        gmail_client = GmailAPIClient(
            access_token, refresh_token, client_id, client_secret, token_uri
        )
        # Fetch new/changed emails since history_id
        emails = gmail_client.fetch_emails_since_history_id(
            notification.email_address, notification.history_id
        )
        logging.info(f"Fetched {len(emails)} emails for {notification.email_address}")
        # Publish each email to email-processing topic with retry
        for email in emails:
            backoff = 1
            for attempt in range(5):
                try:
                    publish_message(EMAIL_PROCESSING_TOPIC, email)
                    break
                except Exception as e:
                    logging.error(
                        f"Failed to publish email to pubsub: {e}, retrying in {backoff}s"
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
            else:
                logging.error(
                    f"ALERT: Failed to publish email after retries. Email: {email}"
                )
                message.nack()
                return
        message.ack()
    except Exception as e:
        logging.error(f"Failed to process message: {e}")
        message.nack()


def run() -> None:
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]

    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, GMAIL_SUBSCRIPTION)
    backoff = 1
    while True:
        try:
            streaming_pull_future = subscriber.subscribe(
                subscription_path, callback=process_gmail_notification
            )
            logging.info(f"Listening for messages on {subscription_path}...")
            streaming_pull_future.result()
        except Exception as e:
            logging.error(f"Subscriber error: {e}, retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    run()
