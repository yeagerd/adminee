import html
import json
import logging
import os
import re
import time
from typing import Any, Dict

from services.email_sync.pubsub_client import publish_message

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST")
EMAIL_PROCESSING_TOPIC = "email-processing"
EMAIL_PARSER_SUBSCRIPTION = os.getenv(
    "EMAIL_PARSER_SUBSCRIPTION", "email-processing-sub"
)

PACKAGE_TRACKER_TOPIC = "package-tracker-events"
SURVEY_EVENTS_TOPIC = "survey-events"
AMAZON_EVENTS_TOPIC = "amazon-events"

logging.basicConfig(level=logging.INFO)

# Regex patterns
UPS_REGEX = re.compile(r"1Z[0-9A-Z]{16}")
FEDEX_REGEX = re.compile(r"\b(\d{12}|\d{15}|\d{4}\s?\d{4}\s?\d{4})\b")
USPS_REGEX = re.compile(r"\d{20,22}")
SURVEY_URL_REGEX = re.compile(r"https://survey\.ourapp\.com/response/[a-zA-Z0-9]+")
AMAZON_STATUS_REGEX = re.compile(
    r"(shipped|expected delivery|delayed|delivered)", re.IGNORECASE
)
AMAZON_ORDER_LINK_REGEX = re.compile(
    r"https://www\.amazon\.com/gp/your-account/order-details\?orderID=[A-Z0-9]+",
    re.IGNORECASE,
)


def sanitize_email_content(content: str) -> str:
    # Basic sanitization: strip HTML tags, unescape, limit length
    text = re.sub(r"<[^>]+>", "", content)
    text = html.unescape(text)
    return text[:10000]  # Limit to 10k chars


def _ensure_list(val: object) -> list[str]:
    if isinstance(val, (list, tuple)):
        return [str(x) for x in val if x is not None]
    if isinstance(val, str):
        return [val]
    if val is None:
        return []
    return [str(val)]


def process_email(message: Any) -> None:
    try:
        data = json.loads(message.data.decode("utf-8"))
        email_body = sanitize_email_content(data.get("body", ""))
        found: Dict[str, Any] = {
            "ups": _ensure_list(UPS_REGEX.findall(email_body)),
            "fedex": _ensure_list(FEDEX_REGEX.findall(email_body)),
            "usps": _ensure_list(USPS_REGEX.findall(email_body)),
            "survey_urls": _ensure_list(SURVEY_URL_REGEX.findall(email_body)),
        }
        # Amazon status extraction
        amazon_status = None
        amazon_order_link = None
        if "amazon" in data.get("from", "").lower() or "amazon" in email_body.lower():
            status_match = AMAZON_STATUS_REGEX.search(email_body)
            if status_match:
                amazon_status = status_match.group(1).lower()
            order_link_match = AMAZON_ORDER_LINK_REGEX.search(email_body)
            if order_link_match:
                amazon_order_link = order_link_match.group(0)
            found["amazon_status"] = amazon_status if amazon_status is not None else ""
            found["amazon_order_link"] = amazon_order_link if amazon_order_link is not None else ""
            if not amazon_status:
                logging.info(f"Unsupported Amazon email format: {email_body[:100]}")
        logging.info(f"Parsed email: {found}")
        # Event publishing
        for ups in found["ups"]:
            event = {"carrier": "UPS", "tracking_number": ups, "raw": email_body}
            try:
                publish_message(PACKAGE_TRACKER_TOPIC, event)
            except Exception as e:
                logging.error(f"Failed to publish UPS event: {e}")
        for fedex in found["fedex"]:
            event = {"carrier": "FedEx", "tracking_number": fedex, "raw": email_body}
            try:
                publish_message(PACKAGE_TRACKER_TOPIC, event)
            except Exception as e:
                logging.error(f"Failed to publish FedEx event: {e}")
        for usps in found["usps"]:
            event = {"carrier": "USPS", "tracking_number": usps, "raw": email_body}
            try:
                publish_message(PACKAGE_TRACKER_TOPIC, event)
            except Exception as e:
                logging.error(f"Failed to publish USPS event: {e}")
        for url in found["survey_urls"]:
            event = {"survey_url": url, "raw": email_body}
            try:
                publish_message(SURVEY_EVENTS_TOPIC, event)
            except Exception as e:
                logging.error(f"Failed to publish survey event: {e}")
        if amazon_status:
            event = {
                "status": amazon_status,
                "order_link": amazon_order_link,
                "raw": email_body,
            }
            try:
                publish_message(AMAZON_EVENTS_TOPIC, event)
            except Exception as e:
                logging.error(f"Failed to publish Amazon event: {e}")
        message.ack()
    except Exception as e:
        logging.error(f"Failed to process email: {e}")
        message.nack()


def run() -> None:
    from google.cloud import pubsub_v1  # type: ignore[attr-defined]

    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(
        PROJECT_ID, EMAIL_PARSER_SUBSCRIPTION
    )
    backoff = 1
    while True:
        try:
            streaming_pull_future = subscriber.subscribe(
                subscription_path, callback=process_email
            )
            logging.info(f"Listening for emails on {subscription_path}...")
            streaming_pull_future.result()
        except Exception as e:
            logging.error(f"Subscriber error: {e}, retrying in {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    run()
