"""
Realistic test data for email_sync service testing.

This module contains sample webhook payloads and email content that mimic
real Gmail and Microsoft webhook notifications, including emails with
tracking numbers, Amazon status updates, and survey URLs.
"""

import json
from typing import Any, Dict, List

# ============================================================================
# Gmail Webhook Test Data
# ============================================================================


def gmail_webhook_payload(
    history_id: str = "12345", email_address: str = "user@example.com"
) -> Dict[str, Any]:
    """Realistic Gmail webhook payload."""
    return {
        "history_id": history_id,
        "email_address": email_address,
        "expiration": "86400000",  # 24 hours in milliseconds
    }


def gmail_webhook_payload_with_multiple_emails() -> Dict[str, Any]:
    """Gmail webhook payload that might trigger multiple email fetches."""
    return {
        "history_id": "67890",
        "email_address": "user@example.com",
        "expiration": "86400000",
    }


# ============================================================================
# Microsoft Webhook Test Data
# ============================================================================


def microsoft_webhook_payload(
    change_type: str = "created", resource: str = "me/messages/1"
) -> Dict[str, Any]:
    """Realistic Microsoft Graph webhook payload."""
    return {
        "value": [
            {
                "changeType": change_type,
                "resource": resource,
                "resourceData": {
                    "id": "AAMkAGVmMDEzMTM4LTZmYWUtNDdkNC1hMDZkLWRmM2NkM2M3ZjQ5OABGAAAAAAAiQ8W967B7TKBjgx9rVEURBwAiIsqMbYjsT5G-T7KzowPTAAAAAAEMAAAiIsqMbYjsT5G-T7KzowPTAAABuF09AAA=",
                    "@odata.type": "#Microsoft.Graph.Message",
                    "@odata.etag": 'W/"CQAAABYAAABuF09AAACXQqEA"',
                    "subject": "Your Amazon order has shipped",
                    "receivedDateTime": "2024-01-15T10:30:00Z",
                },
            }
        ]
    }


def microsoft_webhook_payload_multiple_changes() -> Dict[str, Any]:
    """Microsoft webhook payload with multiple email changes."""
    return {
        "value": [
            {
                "changeType": "created",
                "resource": "me/messages/1",
                "resourceData": {
                    "id": "msg1",
                    "subject": "UPS Tracking Update",
                    "receivedDateTime": "2024-01-15T10:30:00Z",
                },
            },
            {
                "changeType": "created",
                "resource": "me/messages/2",
                "resourceData": {
                    "id": "msg2",
                    "subject": "Survey Request",
                    "receivedDateTime": "2024-01-15T11:00:00Z",
                },
            },
        ]
    }


# ============================================================================
# Sample Email Content with Tracking Numbers
# ============================================================================


def ups_tracking_email() -> Dict[str, Any]:
    """Email with UPS tracking number."""
    return {
        "id": "gmail_ups_123",
        "threadId": "thread_ups_123",
        "labelIds": ["INBOX"],
        "snippet": "Your UPS package has been shipped. Tracking number: 1Z999AA1234567890E",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your UPS package has been shipped"},
                {"name": "From", "value": "UPS <noreply@ups.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 10:30:00 +0000"},
            ],
            "body": {
                "data": "Your package has been shipped and is on its way!<br><br>Tracking Number: 1Z999AA1234567890E<br>Estimated Delivery: January 17, 2024<br><br>Track your package: https://www.ups.com/track?tracknum=1Z999AA1234567890E"
            },
        },
        "internalDate": "1705312200000",
    }


def fedex_tracking_email() -> Dict[str, Any]:
    """Email with FedEx tracking number."""
    return {
        "id": "gmail_fedex_456",
        "threadId": "thread_fedex_456",
        "labelIds": ["INBOX"],
        "snippet": "Your FedEx package is in transit. Tracking: 1234 5678 9012",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your FedEx package is in transit"},
                {"name": "From", "value": "FedEx <tracking@fedex.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 11:00:00 +0000"},
            ],
            "body": {
                "data": "Your FedEx package is on its way!<br><br>Tracking Number: 1234 5678 9012<br>Status: In Transit<br>Estimated Delivery: January 18, 2024<br><br>Track your package: https://www.fedex.com/fedextrack/?trknbr=123456789012"
            },
        },
        "internalDate": "1705312800000",
    }


def usps_tracking_email() -> Dict[str, Any]:
    """Email with USPS tracking number."""
    return {
        "id": "gmail_usps_789",
        "threadId": "thread_usps_789",
        "labelIds": ["INBOX"],
        "snippet": "USPS package delivered. Tracking: 9400111899223856928499",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your USPS package has been delivered"},
                {"name": "From", "value": "USPS <noreply@usps.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 12:00:00 +0000"},
            ],
            "body": {
                "data": "Your USPS package has been delivered!<br><br>Tracking Number: 9400111899223856928499<br>Status: Delivered<br>Delivered to: Front Door<br><br>Track your package: https://tools.usps.com/go/TrackConfirmAction?tLabels=9400111899223856928499"
            },
        },
        "internalDate": "1705316400000",
    }


def multiple_tracking_email() -> Dict[str, Any]:
    """Email with multiple tracking numbers from different carriers."""
    return {
        "id": "gmail_multi_999",
        "threadId": "thread_multi_999",
        "labelIds": ["INBOX"],
        "snippet": "Multiple packages shipped: UPS 1Z999AA1234567890E, FedEx 123456789012",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Multiple packages shipped"},
                {"name": "From", "value": "Shipping Updates <shipping@example.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 13:00:00 +0000"},
            ],
            "body": {
                "data": "Your orders have been shipped!<br><br>Package 1:<br>UPS Tracking: 1Z999AA1234567890E<br>Estimated Delivery: January 17, 2024<br><br>Package 2:<br>FedEx Tracking: 123456789012<br>Estimated Delivery: January 18, 2024<br><br>Package 3:<br>USPS Tracking: 9400111899223856928499<br>Estimated Delivery: January 19, 2024"
            },
        },
        "internalDate": "1705320000000",
    }


# ============================================================================
# Amazon Status Update Emails
# ============================================================================


def amazon_shipped_email() -> Dict[str, Any]:
    """Amazon email indicating package has shipped."""
    return {
        "id": "gmail_amazon_shipped",
        "threadId": "thread_amazon_shipped",
        "labelIds": ["INBOX"],
        "snippet": "Your Amazon order has shipped",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your Amazon order has shipped"},
                {"name": "From", "value": "Amazon <order-update@amazon.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 14:00:00 +0000"},
            ],
            "body": {
                "data": "Your Amazon order has shipped!<br><br>Order #123-4567890-1234567<br>Estimated delivery: January 17, 2024<br><br>View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567"
            },
        },
        "internalDate": "1705323600000",
    }


def amazon_expected_delivery_email() -> Dict[str, Any]:
    """Amazon email with expected delivery update."""
    return {
        "id": "gmail_amazon_delivery",
        "threadId": "thread_amazon_delivery",
        "labelIds": ["INBOX"],
        "snippet": "Your Amazon package is expected to arrive tomorrow",
        "payload": {
            "headers": [
                {
                    "name": "Subject",
                    "value": "Your Amazon package is expected to arrive tomorrow",
                },
                {"name": "From", "value": "Amazon <order-update@amazon.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 15:00:00 +0000"},
            ],
            "body": {
                "data": "Your Amazon package is expected to arrive tomorrow!<br><br>Order #123-4567890-1234567<br>Expected delivery: January 16, 2024<br><br>View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567"
            },
        },
        "internalDate": "1705327200000",
    }


def amazon_delivered_email() -> Dict[str, Any]:
    """Amazon email indicating package has been delivered."""
    return {
        "id": "gmail_amazon_delivered",
        "threadId": "thread_amazon_delivered",
        "labelIds": ["INBOX"],
        "snippet": "Your Amazon package has been delivered",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Your Amazon package has been delivered"},
                {"name": "From", "value": "Amazon <order-update@amazon.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 16:00:00 +0000"},
            ],
            "body": {
                "data": "Your Amazon package has been delivered!<br><br>Order #123-4567890-1234567<br>Delivered: January 15, 2024<br><br>View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567"
            },
        },
        "internalDate": "1705330800000",
    }


def amazon_delayed_email() -> Dict[str, Any]:
    """Amazon email indicating delivery has been delayed."""
    return {
        "id": "gmail_amazon_delayed",
        "threadId": "thread_amazon_delayed",
        "labelIds": ["INBOX"],
        "snippet": "Your Amazon package delivery has been delayed",
        "payload": {
            "headers": [
                {
                    "name": "Subject",
                    "value": "Your Amazon package delivery has been delayed",
                },
                {"name": "From", "value": "Amazon <order-update@amazon.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 17:00:00 +0000"},
            ],
            "body": {
                "data": "Your Amazon package delivery has been delayed.<br><br>Order #123-4567890-1234567<br>New estimated delivery: January 19, 2024<br><br>View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567"
            },
        },
        "internalDate": "1705334400000",
    }


# ============================================================================
# Survey Response Emails
# ============================================================================


def survey_response_email() -> Dict[str, Any]:
    """Email containing a survey response URL."""
    return {
        "id": "gmail_survey_abc",
        "threadId": "thread_survey_abc",
        "labelIds": ["INBOX"],
        "snippet": "Please complete our survey",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Please complete our survey"},
                {"name": "From", "value": "Survey Team <surveys@example.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 18:00:00 +0000"},
            ],
            "body": {
                "data": "Thank you for your recent purchase!<br><br>We'd love to hear your feedback. Please complete our survey:<br><br>https://survey.ourapp.com/response/abc123<br><br>Your feedback helps us improve our service."
            },
        },
        "internalDate": "1705338000000",
    }


def multiple_survey_emails() -> Dict[str, Any]:
    """Email with multiple survey URLs."""
    return {
        "id": "gmail_survey_multi",
        "threadId": "thread_survey_multi",
        "labelIds": ["INBOX"],
        "snippet": "Multiple surveys available",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Multiple surveys available"},
                {"name": "From", "value": "Survey Team <surveys@example.com>"},
                {"name": "To", "value": "user@example.com"},
                {"name": "Date", "value": "Mon, 15 Jan 2024 19:00:00 +0000"},
            ],
            "body": {
                "data": "We have multiple surveys for you to complete:<br><br>Product Feedback: https://survey.ourapp.com/response/def456<br>Service Quality: https://survey.ourapp.com/response/ghi789<br>Overall Experience: https://survey.ourapp.com/response/jkl012"
            },
        },
        "internalDate": "1705341600000",
    }


# ============================================================================
# Microsoft Graph Email Format
# ============================================================================


def microsoft_ups_email() -> Dict[str, Any]:
    """Microsoft Graph format email with UPS tracking."""
    return {
        "id": "outlook_ups_123",
        "subject": "Your UPS package has been shipped",
        "from": {"emailAddress": {"address": "noreply@ups.com", "name": "UPS"}},
        "toRecipients": [
            {"emailAddress": {"address": "user@example.com", "name": "User"}}
        ],
        "receivedDateTime": "2024-01-15T10:30:00Z",
        "bodyPreview": "Your package has been shipped and is on its way!",
        "body": {
            "contentType": "HTML",
            "content": "Your package has been shipped and is on its way!<br><br>Tracking Number: 1Z999AA1234567890E<br>Estimated Delivery: January 17, 2024<br><br>Track your package: https://www.ups.com/track?tracknum=1Z999AA1234567890E",
        },
    }


def microsoft_amazon_email() -> Dict[str, Any]:
    """Microsoft Graph format email with Amazon status."""
    return {
        "id": "outlook_amazon_456",
        "subject": "Your Amazon order has shipped",
        "from": {
            "emailAddress": {"address": "order-update@amazon.com", "name": "Amazon"}
        },
        "toRecipients": [
            {"emailAddress": {"address": "user@example.com", "name": "User"}}
        ],
        "receivedDateTime": "2024-01-15T14:00:00Z",
        "bodyPreview": "Your Amazon order has shipped!",
        "body": {
            "contentType": "HTML",
            "content": "Your Amazon order has shipped!<br><br>Order #123-4567890-1234567<br>Estimated delivery: January 17, 2024<br><br>View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567",
        },
    }


def microsoft_survey_email() -> Dict[str, Any]:
    """Microsoft Graph format email with survey URL."""
    return {
        "id": "outlook_survey_789",
        "subject": "Please complete our survey",
        "from": {
            "emailAddress": {"address": "surveys@example.com", "name": "Survey Team"}
        },
        "toRecipients": [
            {"emailAddress": {"address": "user@example.com", "name": "User"}}
        ],
        "receivedDateTime": "2024-01-15T18:00:00Z",
        "bodyPreview": "Thank you for your recent purchase!",
        "body": {
            "contentType": "HTML",
            "content": "Thank you for your recent purchase!<br><br>We'd love to hear your feedback. Please complete our survey:<br><br>https://survey.ourapp.com/response/abc123<br><br>Your feedback helps us improve our service.",
        },
    }


# ============================================================================
# Test Data Collections
# ============================================================================


def get_all_tracking_emails() -> List[Dict[str, Any]]:
    """Get all email samples with tracking numbers."""
    return [
        ups_tracking_email(),
        fedex_tracking_email(),
        usps_tracking_email(),
        multiple_tracking_email(),
    ]


def get_all_amazon_emails() -> List[Dict[str, Any]]:
    """Get all Amazon status update emails."""
    return [
        amazon_shipped_email(),
        amazon_expected_delivery_email(),
        amazon_delivered_email(),
        amazon_delayed_email(),
    ]


def get_all_survey_emails() -> List[Dict[str, Any]]:
    """Get all survey response emails."""
    return [survey_response_email(), multiple_survey_emails()]


def get_all_microsoft_emails() -> List[Dict[str, Any]]:
    """Get all Microsoft Graph format emails."""
    return [microsoft_ups_email(), microsoft_amazon_email(), microsoft_survey_email()]


def get_all_test_emails() -> List[Dict[str, Any]]:
    """Get all test email samples."""
    return (
        get_all_tracking_emails()
        + get_all_amazon_emails()
        + get_all_survey_emails()
        + get_all_microsoft_emails()
    )


# ============================================================================
# Utility Functions
# ============================================================================


def create_pubsub_message(data: Dict[str, Any]) -> bytes:
    """Create a pubsub message from data."""
    return json.dumps(data).encode("utf-8")


def create_mock_message(data: Dict[str, Any]) -> Any:
    """Create a mock pubsub message object for testing."""

    class MockMessage:
        def __init__(self, data_dict: Dict[str, Any]):
            self.data = json.dumps(data_dict).encode("utf-8")
            self.acked = False
            self.nacked = False

        def ack(self):
            self.acked = True

        def nack(self):
            self.nacked = True

    return MockMessage(data)
