import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from services.common.settings import BaseSettings, Field
from services.email_sync.email_tracking import email_tracking_service
from services.email_sync.microsoft_graph_client import MicrosoftGraphClient
from services.email_sync.pubsub_client import publish_message


class MicrosoftSyncSettings(BaseSettings):
    GOOGLE_CLOUD_PROJECT: str = Field(..., description="GCP project ID")
    PUBSUB_EMULATOR_HOST: str = Field("", description="PubSub emulator host")
    MICROSOFT_SUBSCRIPTION: str = Field(
        "microsoft-notifications-sub", description="Microsoft subscription name"
    )
    MS_GRAPH_ACCESS_TOKEN: str = Field(
        "test-access-token", description="MS Graph access token"
    )


MICROSOFT_TOPIC = "microsoft-notifications"
EMAIL_PROCESSING_TOPIC = "email-processing"

logging.basicConfig(level=logging.INFO)


def process_microsoft_notification(message: Any) -> None:
    settings = MicrosoftSyncSettings()

    try:
        data = json.loads(message.data.decode("utf-8"))
        logging.info(f"Processing Microsoft notification: {data}")

        # Extract user email from notification (this would come from the webhook)
        # For now, we'll use a default or extract from the notification
        user_email = data.get(
            "user_email", "user@example.com"
        )  # TODO: Extract from notification

        # TODO: Retrieve access token for the user (mocked for now)
        graph_client = MicrosoftGraphClient(settings.MS_GRAPH_ACCESS_TOKEN)

        # Get the last processed delta link for this user
        last_delta_link = email_tracking_service.get_microsoft_delta_link(user_email)

        # Fetch emails using notification or delta link
        emails = []
        if data.get("value"):  # Change notification
            emails = graph_client.fetch_emails_from_notification(data)
        elif last_delta_link:  # Delta sync
            delta_result = graph_client.get_delta_emails(last_delta_link)
            emails = delta_result.get("emails", [])
            # Update delta link for next sync
            new_delta_link = delta_result.get("delta_link")
            if new_delta_link:
                email_tracking_service.update_processing_state(
                    user_email=user_email,
                    provider="microsoft",
                    delta_link=new_delta_link,
                )

        logging.info(
            f"Fetched {len(emails)} emails from Microsoft Graph for {user_email}"
        )

        # Process each email and track state
        processed_count = 0
        for email in emails:
            # Check if we've already processed this email
            if email_tracking_service.is_email_processed(
                user_email, "microsoft", email["id"]
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
                else:
                    logging.error(
                        f"ALERT: Failed to publish email after retries. "
                        f"Email: {email['id']}"
                    )
                message.nack()
                return

            # Mark email as processed
            email_timestamp = None
            if email.get("receivedDateTime"):
                try:
                    # Microsoft uses ISO 8601 format
                    email_timestamp = datetime.fromisoformat(
                        email["receivedDateTime"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    email_timestamp = datetime.now(timezone.utc)

            email_tracking_service.mark_email_processed(
                user_email, "microsoft", email["id"], email_timestamp
            )
            processed_count += 1

        logging.info(
            f"Successfully processed {processed_count} new emails for {user_email}"
        )
        message.ack()

    except Exception as e:
        logging.error(f"Failed to process message: {e}")
        message.nack()


def run() -> None:
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]

    settings = MicrosoftSyncSettings()
    PROJECT_ID = settings.GOOGLE_CLOUD_PROJECT
    PUBSUB_EMULATOR_HOST = settings.PUBSUB_EMULATOR_HOST
    MICROSOFT_SUBSCRIPTION = settings.MICROSOFT_SUBSCRIPTION
    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    if not PROJECT_ID:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is not set.")
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
