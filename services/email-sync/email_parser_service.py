import os
import re
import time
import logging
import json

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST")
EMAIL_PROCESSING_TOPIC = "email-processing"
EMAIL_PARSER_SUBSCRIPTION = os.getenv("EMAIL_PARSER_SUBSCRIPTION", "email-processing-sub")

logging.basicConfig(level=logging.INFO)

# Regex patterns
UPS_REGEX = re.compile(r"1Z[0-9A-Z]{16}")
FEDEX_REGEX = re.compile(r"(\d{4}\s?\d{4}\s?\d{4}|\d{12})")
USPS_REGEX = re.compile(r"\d{20,22}")
SURVEY_URL_REGEX = re.compile(r"https://survey\.ourapp\.com/response/[a-zA-Z0-9]+")


def process_email(message):
    try:
        data = json.loads(message.data.decode("utf-8"))
        email_body = data.get("body", "")
        found = {
            "ups": UPS_REGEX.findall(email_body),
            "fedex": FEDEX_REGEX.findall(email_body),
            "usps": USPS_REGEX.findall(email_body),
            "survey_urls": SURVEY_URL_REGEX.findall(email_body),
        }
        logging.info(f"Parsed email: {found}")
        # TODO: Amazon status, event publishing, sanitization
        message.ack()
    except Exception as e:
        logging.error(f"Failed to process email: {e}")
        message.nack()


def run():
    from google.cloud import pubsub_v1
    if PUBSUB_EMULATOR_HOST:
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, EMAIL_PARSER_SUBSCRIPTION)
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