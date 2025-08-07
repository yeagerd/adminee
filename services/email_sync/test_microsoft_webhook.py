import logging
import os
from unittest.mock import patch

# Set environment variables before importing app
os.environ["MICROSOFT_WEBHOOK_SECRET"] = "test-microsoft-webhook-secret"
os.environ["GMAIL_WEBHOOK_SECRET"] = "test-gmail-webhook-secret"
os.environ["PYTHON_ENV"] = "test"

from services.email_sync.app import app
from services.email_sync.test_data import (
    microsoft_webhook_payload,
    microsoft_webhook_payload_multiple_changes,
)


def valid_payload():
    return {"value": [{"changeType": "created", "resource": "me/messages/1"}]}


class TestMicrosoftWebhook:
    """Comprehensive tests for Microsoft webhook endpoint."""

    def test_microsoft_webhook_success(self):
        """Test successful Microsoft webhook processing."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_invalid_signature(self):
        """Test Microsoft webhook with invalid signature."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": "wrong-secret"},
                )
                assert resp.status_code == 401
                mock_publish.assert_not_called()

    def test_microsoft_webhook_missing_signature(self):
        """Test Microsoft webhook with missing signature header."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                )
                assert resp.status_code == 401
                mock_publish.assert_not_called()

    def test_microsoft_webhook_empty_signature(self):
        """Test Microsoft webhook with empty signature header."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": ""},
                )
                assert resp.status_code == 401
                mock_publish.assert_not_called()

    def test_microsoft_webhook_invalid_payload(self):
        """Test Microsoft webhook with invalid JSON payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    data="not a json",
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                    content_type="application/json",
                )
                assert resp.status_code == 400
                mock_publish.assert_not_called()

    def test_microsoft_webhook_missing_value_field(self):
        """Test Microsoft webhook with payload missing 'value' field."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json={"invalid": "payload"},
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 400
                mock_publish.assert_not_called()

    def test_microsoft_webhook_empty_value_field(self):
        """Test Microsoft webhook with empty 'value' field."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json={"value": []},
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                mock_publish.assert_called_once()

    def test_microsoft_webhook_pubsub_failure(self):
        """Test Microsoft webhook when pubsub publishing fails."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message",
            side_effect=Exception("pubsub error"),
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 400
                mock_publish.assert_called_once()

    def test_microsoft_webhook_with_realistic_payload(self):
        """Test Microsoft webhook with realistic payload from test data."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload()
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_with_multiple_changes(self):
        """Test Microsoft webhook with multiple email changes."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload_multiple_changes()
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_different_change_types(self):
        """Test Microsoft webhook with different change types."""
        change_types = ["created", "updated", "deleted"]

        for change_type in change_types:
            with patch(
                "services.email_sync.microsoft_webhook.publish_message"
            ) as mock_publish:
                with app.test_client() as client:
                    payload = microsoft_webhook_payload(change_type=change_type)
                    resp = client.post(
                        "/microsoft/webhook",
                        json=payload,
                        headers={
                            "X-Microsoft-Signature": "test-microsoft-webhook-secret"
                        },
                    )
                    assert resp.status_code == 200
                    assert resp.json["status"] == "published"
                    mock_publish.assert_called_once()

    def test_microsoft_webhook_different_resources(self):
        """Test Microsoft webhook with different resource types."""
        resources = [
            "me/messages/1",
            "me/messages/12345",
            "users/user@example.com/messages/1",
            "me/mailFolders/Inbox/messages/1",
        ]

        for resource in resources:
            with patch(
                "services.email_sync.microsoft_webhook.publish_message"
            ) as mock_publish:
                with app.test_client() as client:
                    payload = microsoft_webhook_payload(resource=resource)
                    resp = client.post(
                        "/microsoft/webhook",
                        json=payload,
                        headers={
                            "X-Microsoft-Signature": "test-microsoft-webhook-secret"
                        },
                    )
                    assert resp.status_code == 200
                    assert resp.json["status"] == "published"
                    mock_publish.assert_called_once()

    def test_microsoft_webhook_large_payload(self):
        """Test Microsoft webhook with large payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                # Create a large payload with many changes
                large_payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": f"me/messages/{i}",
                            "resourceData": {
                                "id": f"msg_{i}",
                                "subject": f"Email {i}",
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                            },
                        }
                        for i in range(100)
                    ]
                }

                resp = client.post(
                    "/microsoft/webhook",
                    json=large_payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_malformed_json(self):
        """Test Microsoft webhook with malformed JSON."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    data=(
                        '{"value": [{"changeType": "created", "resource": "me/messages/1"'
                    ),  # Incomplete JSON
                    headers={
                        "X-Microsoft-Signature": "test-microsoft-webhook-secret",
                        "Content-Type": "application/json",
                    },
                )
                assert resp.status_code == 400
                mock_publish.assert_not_called()

    def test_microsoft_webhook_wrong_content_type(self):
        """Test Microsoft webhook with wrong content type."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    data='{"value": []}',
                    headers={
                        "X-Microsoft-Signature": "test-microsoft-webhook-secret",
                        "Content-Type": "text/plain",
                    },
                )
                # Should still work as Flask can parse JSON even with wrong content type
                assert resp.status_code == 200
                mock_publish.assert_called_once()

    def test_microsoft_webhook_nested_value_field(self):
        """Test Microsoft webhook with nested 'value' field."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "metadata": {"version": "1.0"},
                    "value": [{"changeType": "created", "resource": "me/messages/1"}],
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_logging_on_success(self, caplog):
        """Test that successful Microsoft webhook requests are logged."""
        caplog.set_level(logging.INFO)

        with patch("services.email_sync.microsoft_webhook.publish_message"):
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                # Note: The current implementation doesn't log success, only warnings/errors
                # This test documents the current behavior

    def test_microsoft_webhook_logging_on_unauthorized(self, caplog):
        """Test that unauthorized Microsoft webhook attempts are logged."""
        caplog.set_level(logging.WARNING)

        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": "wrong-secret"},
                )
                assert resp.status_code == 401
                assert "Unauthorized Microsoft webhook attempt" in caplog.text
                mock_publish.assert_not_called()

    def test_microsoft_webhook_logging_on_invalid_payload(self, caplog):
        """Test that invalid Microsoft webhook payloads are logged."""
        caplog.set_level(logging.ERROR)

        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json={"invalid": "payload"},
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 400
                assert (
                    "Invalid Microsoft webhook payload: missing 'value' field"
                    in caplog.text
                )
                mock_publish.assert_not_called()

    def test_microsoft_webhook_logging_on_pubsub_failure(self, caplog):
        """Test that pubsub failures are logged."""
        caplog.set_level(logging.ERROR)

        with patch(
            "services.email_sync.microsoft_webhook.publish_message",
            side_effect=Exception("pubsub error"),
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 400
                assert (
                    "Failed to process Microsoft webhook: pubsub error" in caplog.text
                )
                mock_publish.assert_called_once()

    def test_microsoft_webhook_publish_message_called_with_correct_topic(self):
        """Test that publish_message is called with the correct topic."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                resp = client.post(
                    "/microsoft/webhook",
                    json=valid_payload(),
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200

                # Verify publish_message was called with correct topic
                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[0][0] == "microsoft-notifications"  # Topic
                assert call_args[0][1] == valid_payload()  # Data

    def test_microsoft_webhook_publish_message_called_with_realistic_payload(self):
        """Test that publish_message is called with realistic payload data."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload()
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200

                # Verify publish_message was called with the exact payload
                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[0][0] == "microsoft-notifications"
                assert call_args[0][1] == payload

    def test_microsoft_webhook_handles_unicode_characters(self):
        """Test Microsoft webhook handles Unicode characters in payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {
                                "id": "msg1",
                                "subject": "📧 Email with emoji 🚀",
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                            },
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_special_characters(self):
        """Test Microsoft webhook handles special characters in payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {
                                "id": "msg1",
                                "subject": (
                                    "Email with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
                                ),
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                            },
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_null_values(self):
        """Test Microsoft webhook handles null values in payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {
                                "id": "msg1",
                                "subject": None,
                                "receivedDateTime": None,
                            },
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_missing_resource_data(self):
        """Test Microsoft webhook handles missing resourceData field."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            # Missing resourceData field
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_empty_resource_data(self):
        """Test Microsoft webhook handles empty resourceData field."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {},
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_missing_change_type(self):
        """Test Microsoft webhook handles missing changeType field."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "resource": "me/messages/1"
                            # Missing changeType field
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_missing_resource(self):
        """Test Microsoft webhook handles missing resource field."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created"
                            # Missing resource field
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_extra_fields(self):
        """Test Microsoft webhook handles extra fields in payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "extraField1": "extra value 1",
                            "extraField2": {"nested": "value"},
                            "resourceData": {
                                "id": "msg1",
                                "subject": "Test email",
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                            },
                        }
                    ],
                    "extraTopLevelField": "extra top level value",
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_deep_nested_structures(self):
        """Test Microsoft webhook handles deeply nested structures."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {
                                "id": "msg1",
                                "subject": "Test email",
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                                "nested": {
                                    "level1": {
                                        "level2": {
                                            "level3": {
                                                "level4": {"level5": "deep value"}
                                            }
                                        }
                                    }
                                },
                            },
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_array_values(self):
        """Test Microsoft webhook handles array values in payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {
                                "id": "msg1",
                                "subject": "Test email",
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                                "arrayField": [1, 2, 3, "string", {"nested": "object"}],
                                "emptyArray": [],
                            },
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_boolean_values(self):
        """Test Microsoft webhook handles boolean values in payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {
                                "id": "msg1",
                                "subject": "Test email",
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                                "isRead": True,
                                "isDraft": False,
                                "hasAttachments": True,
                            },
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()

    def test_microsoft_webhook_handles_numeric_values(self):
        """Test Microsoft webhook handles numeric values in payload."""
        with patch(
            "services.email_sync.microsoft_webhook.publish_message"
        ) as mock_publish:
            with app.test_client() as client:
                payload = {
                    "value": [
                        {
                            "changeType": "created",
                            "resource": "me/messages/1",
                            "resourceData": {
                                "id": "msg1",
                                "subject": "Test email",
                                "receivedDateTime": "2024-01-15T10:30:00Z",
                                "size": 1024,
                                "importance": 1,
                                "conversationId": 12345,
                                "floatValue": 3.14159,
                            },
                        }
                    ]
                }
                resp = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                assert resp.status_code == 200
                assert resp.json["status"] == "published"
                mock_publish.assert_called_once()
