import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from services.common.settings import BaseSettings, Field
from services.email_sync.email_tracking import email_tracking_service
from services.email_sync.gmail_api_client import GmailAPIClient
from services.email_sync.pubsub_client import publish_message
from services.email_sync.schemas import GmailNotification


class GmailSyncSettings(BaseSettings):
    GOOGLE_CLOUD_PROJECT: str = Field(..., description="GCP project ID")
    PUBSUB_EMULATOR_HOST: str = Field("", description="PubSub emulator host")
    GMAIL_SUBSCRIPTION: str = Field(
        "gmail-notifications-sub", description="Gmail subscription name"
    )
    GMAIL_ACCESS_TOKEN: str = Field(
        "test-access-token", description="Gmail access token"
    )
    GMAIL_REFRESH_TOKEN: str = Field(
        "test-refresh-token", description="Gmail refresh token"
    )
    GMAIL_CLIENT_ID: str = Field("test-client-id", description="Gmail client id")
    GMAIL_CLIENT_SECRET: str = Field(
        "test-client-secret", description="Gmail client secret"
    )
    GMAIL_TOKEN_URI: str = Field(
        "https://oauth2.googleapis.com/token", description="Gmail token URI"
    )


logging.basicConfig(level=logging.INFO)


def process_gmail_notification(message: Any) -> None:
    settings = GmailSyncSettings()
    EMAIL_PROCESSING_TOPIC = "email-processing"

    try:
        data = json.loads(message.data.decode("utf-8"))
        notification = GmailNotification(**data)
        logging.info(f"Processing Gmail notification: {notification}")

        # TODO: Retrieve tokens and client info for the user (mocked for now)
        gmail_client = GmailAPIClient(
            settings.GMAIL_ACCESS_TOKEN,
            settings.GMAIL_REFRESH_TOKEN,
            settings.GMAIL_CLIENT_ID,
            settings.GMAIL_CLIENT_SECRET,
            settings.GMAIL_TOKEN_URI,
        )

        # Get the last processed history ID for this user
        last_history_id = email_tracking_service.get_gmail_history_id(
            notification.email_address
        )

        # Use the notification history ID or fall back to last known
        start_history_id = last_history_id or notification.history_id

        # Fetch new/changed emails since the history ID
        emails = gmail_client.fetch_emails_since_history_id(
            notification.email_address, start_history_id
        )

        logging.info(f"Fetched {len(emails)} emails for {notification.email_address}")

        # Track the latest history ID from the notification
        latest_history_id = notification.history_id

        # Process each email and track state
        processed_count = 0
        for email in emails:
            # Check if we've already processed this email
            if email_tracking_service.is_email_processed(
                notification.email_address, "gmail", email["id"]
            ):
                logging.info(f"Email {email['id']} already processed, skipping")
                continue

            # Publish email to processing topic with retry
            backoff = 1
            for attempt in range(5):
                try:
                    publish_message(EMAIL_PROCESSING_TOPIC, email)
                    break
                except Exception as e:
                    logging.error(
                        f"Failed to publish email to pubsub: {e}, "
                        f"retrying in {backoff}s"
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 60)
            else:
                logging.error(
                    f"ALERT: Failed to publish email after retries. "
                    f"Email: {email['id']}"
                )
                message.nack()
                return

            # Mark email as processed
            email_timestamp = None
            if email.get("internalDate"):
                try:
                    # Gmail internalDate is in milliseconds since epoch
                    timestamp_ms = int(email["internalDate"])
                    email_timestamp = datetime.fromtimestamp(
                        timestamp_ms / 1000, tz=timezone.utc
                    )
                except (ValueError, TypeError):
                    email_timestamp = datetime.now(timezone.utc)

            email_tracking_service.mark_email_processed(
                notification.email_address, "gmail", email["id"], email_timestamp
            )
            processed_count += 1

        # Update the history ID tracking
        if latest_history_id:
            email_tracking_service.update_processing_state(
                user_email=notification.email_address,
                provider="gmail",
                history_id=latest_history_id,
            )

        logging.info(
            f"Successfully processed {processed_count} new emails for "
            f"{notification.email_address}"
        )
        message.ack()

    except Exception as e:
        logging.error(f"Failed to process message: {e}")
        message.nack()


def run() -> None:
    settings = GmailSyncSettings()
    PROJECT_ID = settings.GOOGLE_CLOUD_PROJECT
    PUBSUB_EMULATOR_HOST = settings.PUBSUB_EMULATOR_HOST
    GMAIL_SUBSCRIPTION = settings.GMAIL_SUBSCRIPTION
    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    if not PROJECT_ID:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set.")
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]

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
