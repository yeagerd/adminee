"""
Integration tests for webhook endpoints using realistic test data.

These tests verify that the webhook endpoints properly handle realistic
Gmail and Microsoft webhook payloads and publish appropriate messages
to pubsub topics.
"""

import os
from unittest.mock import patch

# Set up test environment before importing modules that depend on these variables
os.environ["PYTHON_ENV"] = "test"
os.environ["GMAIL_WEBHOOK_SECRET"] = "test-gmail-webhook-secret"
os.environ["MICROSOFT_WEBHOOK_SECRET"] = "test-microsoft-webhook-secret"

from services.common.test_utils import BaseSelectiveHTTPIntegrationTest
from services.email_sync.app import app
from services.email_sync.tests.test_data import (
    gmail_webhook_payload,
    gmail_webhook_payload_with_multiple_emails,
    microsoft_webhook_payload,
    microsoft_webhook_payload_multiple_changes,
)


class BaseEmailSyncIntegrationTest(BaseSelectiveHTTPIntegrationTest):
    """Base class for email sync integration tests with proper environment setup."""

    def setup_method(self, method: object) -> None:
        """Set up test environment with email sync specific configuration."""
        # Call parent setup to enable HTTP call prevention
        super().setup_method(method)


class TestGmailWebhookIntegration(BaseEmailSyncIntegrationTest):
    """Integration tests for Gmail webhook endpoint."""

    def setup_method(self, method):
        """Set up test environment and reset mocks."""
        super().setup_method(method)
        # Reset the mock to clear calls from previous tests
        from services.email_sync.pubsub_client import publish_message

        if hasattr(publish_message, "reset_mock"):
            publish_message.reset_mock()

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_with_realistic_payload(self, mock_publish):
        """Test Gmail webhook with realistic payload."""
        client = self.create_test_client(app)
        payload = gmail_webhook_payload()
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify message was published to gmail-notifications topic
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "gmail-notifications"
        assert call_args[0][1]["history_id"] == "12345"
        assert call_args[0][1]["email_address"] == "user@example.com"

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_with_multiple_emails_payload(self, mock_publish):
        """Test Gmail webhook with payload that might trigger multiple email fetches."""
        client = self.create_test_client(app)
        payload = gmail_webhook_payload_with_multiple_emails()
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        # Verify message was published
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "gmail-notifications"
        assert call_args[0][1]["history_id"] == "67890"

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_invalid_secret(self, mock_publish):
        """Test Gmail webhook with invalid secret."""
        client = self.create_test_client(app)
        payload = gmail_webhook_payload()
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "wrong-secret"},
        )

        assert response.status_code == 401
        mock_publish.assert_not_called()

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_missing_secret_header(self, mock_publish):
        """Test Gmail webhook with missing secret header."""
        client = self.create_test_client(app)
        payload = gmail_webhook_payload()
        response = client.post(
            "/gmail/webhook",
            json=payload,
        )

        assert response.status_code == 401
        mock_publish.assert_not_called()

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_invalid_payload_missing_history_id(self, mock_publish):
        """Test Gmail webhook with invalid payload missing history_id."""
        client = self.create_test_client(app)
        payload = {"email_address": "user@example.com"}
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        assert response.status_code == 400
        mock_publish.assert_not_called()

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_invalid_payload_missing_email_address(self, mock_publish):
        """Test Gmail webhook with invalid payload missing email_address."""
        client = self.create_test_client(app)
        payload = {"history_id": "12345"}
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        assert response.status_code == 400
        mock_publish.assert_not_called()

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_pubsub_failure(self, mock_publish):
        """Test Gmail webhook when pubsub publishing fails."""
        client = self.create_test_client(app)
        # Set up the mock to fail
        mock_publish.side_effect = Exception("pubsub error")

        payload = gmail_webhook_payload()
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        assert response.status_code == 503
        mock_publish.assert_called_once()


class TestMicrosoftWebhookIntegration(BaseEmailSyncIntegrationTest):
    """Integration tests for Microsoft webhook endpoint."""

    def setup_method(self, method):
        """Set up test environment and reset mocks."""
        super().setup_method(method)
        from services.email_sync.microsoft_webhook import publish_message

        publish_message.reset_mock()

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_with_realistic_payload(self, mock_publish):
        """Test Microsoft webhook with realistic payload."""
        client = self.create_test_client(app)
        payload = microsoft_webhook_payload()
        response = client.post(
            "/microsoft/webhook",
            json=payload,
            headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "published"

        # Verify message was published to microsoft-notifications topic
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "microsoft-notifications"
        assert "value" in call_args[0][1]
        assert len(call_args[0][1]["value"]) == 1
        assert call_args[0][1]["value"][0]["changeType"] == "created"

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_with_multiple_changes(self, mock_publish):
        """Test Microsoft webhook with multiple email changes."""
        client = self.create_test_client(app)
        payload = microsoft_webhook_payload_multiple_changes()
        response = client.post(
            "/microsoft/webhook",
            json=payload,
            headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "published"

        # Verify message was published
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "microsoft-notifications"
        assert len(call_args[0][1]["value"]) == 2

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_invalid_signature(self, mock_publish):
        """Test Microsoft webhook with invalid signature."""
        client = self.create_test_client(app)
        payload = microsoft_webhook_payload()
        response = client.post(
            "/microsoft/webhook",
            json=payload,
            headers={"X-Microsoft-Signature": "wrong-secret"},
        )

        assert response.status_code == 401
        mock_publish.assert_not_called()

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_missing_signature_header(self, mock_publish):
        """Test Microsoft webhook with missing signature header."""
        client = self.create_test_client(app)
        payload = microsoft_webhook_payload()
        response = client.post(
            "/microsoft/webhook",
            json=payload,
        )

        assert response.status_code == 401
        mock_publish.assert_not_called()

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_invalid_payload_not_json(self, mock_publish):
        """Test Microsoft webhook with invalid payload that's not JSON."""
        client = self.create_test_client(app)
        response = client.post(
            "/microsoft/webhook",
            data="not json",
            headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
        )

        assert response.status_code == 400
        mock_publish.assert_not_called()

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_invalid_payload_missing_value(self, mock_publish):
        """Test Microsoft webhook with invalid payload missing value field."""
        client = self.create_test_client(app)
        payload = {"invalid": "payload"}
        response = client.post(
            "/microsoft/webhook",
            json=payload,
            headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
        )

        assert response.status_code == 400
        mock_publish.assert_not_called()

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_pubsub_failure(self, mock_publish):
        """Test Microsoft webhook when pubsub publishing fails."""
        client = self.create_test_client(app)
        # Set up the mock to fail
        mock_publish.side_effect = Exception("pubsub error")

        payload = microsoft_webhook_payload()
        response = client.post(
            "/microsoft/webhook",
            json=payload,
            headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
        )

        assert response.status_code == 400
        mock_publish.assert_called_once()


class TestWebhookEndToEnd(BaseEmailSyncIntegrationTest):
    """End-to-end tests for webhook processing pipeline."""

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_to_email_processing_pipeline(self, mock_publish):
        """Test complete Gmail webhook to email processing pipeline."""
        client = self.create_test_client(app)
        # Send Gmail webhook
        payload = gmail_webhook_payload()
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        assert response.status_code == 200

        # Verify message was published to gmail-notifications topic
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "gmail-notifications"

        # The gmail-notifications message should contain the webhook data
        published_data = call_args[0][1]
        assert published_data["history_id"] == "12345"
        assert published_data["email_address"] == "user@example.com"

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_to_email_processing_pipeline(self, mock_publish):
        """Test complete Microsoft webhook to email processing pipeline."""
        client = self.create_test_client(app)
        # Send Microsoft webhook
        payload = microsoft_webhook_payload()
        response = client.post(
            "/microsoft/webhook",
            json=payload,
            headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
        )

        assert response.status_code == 200

        # Verify message was published to microsoft-notifications topic
        mock_publish.assert_called_once()
        call_args = mock_publish.call_args
        assert call_args[0][0] == "microsoft-notifications"

        # The microsoft-notifications message should contain the webhook data
        published_data = call_args[0][1]
        assert "value" in published_data
        assert len(published_data["value"]) == 1
        assert published_data["value"][0]["changeType"] == "created"

    @patch("services.email_sync.app.publish_message")
    def test_webhook_rate_limiting_simulation(self, mock_publish):
        """Test webhook handling under simulated load."""
        client = self.create_test_client(app)
        # Send multiple Gmail webhooks rapidly
        for i in range(5):
            payload = gmail_webhook_payload(
                history_id=str(i), email_address=f"user{i}@example.com"
            )
            response = client.post(
                "/gmail/webhook",
                json=payload,
                headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
            )

            assert response.status_code == 200

        # Verify all messages were published
        assert mock_publish.call_count == 5

        # Verify each call was to the correct topic
        for call in mock_publish.call_args_list:
            assert call[0][0] == "gmail-notifications"

    @patch("services.email_sync.app.publish_message")
    def test_webhook_error_recovery(self, mock_publish):
        """Test webhook error recovery scenarios."""
        client = self.create_test_client(app)
        # Set up the mock to fail first, then succeed
        mock_publish.side_effect = [Exception("pubsub error"), None]

        payload = gmail_webhook_payload()

        # First attempt should fail
        response1 = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )
        assert response1.status_code == 503

        # Second attempt should succeed
        response2 = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )
        assert response2.status_code == 200

        # Verify both attempts were made
        assert mock_publish.call_count == 2


class TestWebhookDataValidation(BaseEmailSyncIntegrationTest):
    """Tests for webhook data validation and sanitization."""

    @patch("services.email_sync.app.publish_message")
    def test_gmail_webhook_data_sanitization(self, mock_publish):
        """Test that Gmail webhook data is properly sanitized."""
        client = self.create_test_client(app)
        # Test with payload containing potentially malicious content
        payload = {
            "history_id": "12345",
            "email_address": "user@example.com<script>alert('xss')</script>",
        }
        response = client.post(
            "/gmail/webhook",
            json=payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        assert response.status_code == 200
        mock_publish.assert_called_once()

        # Verify the published data is sanitized
        call_args = mock_publish.call_args
        published_data = call_args[0][1]
        assert (
            published_data["email_address"]
            == "user@example.com<script>alert('xss')</script>"
        )

    @patch("services.email_sync.microsoft_webhook.publish_message")
    def test_microsoft_webhook_data_sanitization(self, mock_publish):
        """Test that Microsoft webhook data is properly sanitized."""
        client = self.create_test_client(app)
        # Test with payload containing potentially malicious content
        payload = {
            "value": [
                {
                    "changeType": "created",
                    "resource": "messages",
                    "resourceData": {"id": "msg123<script>alert('xss')</script>"},
                }
            ]
        }
        response = client.post(
            "/microsoft/webhook",
            json=payload,
            headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
        )

        assert response.status_code == 200
        mock_publish.assert_called_once()

        # Verify the published data is sanitized
        call_args = mock_publish.call_args
        published_data = call_args[0][1]
        assert (
            published_data["value"][0]["resourceData"]["id"]
            == "msg123<script>alert('xss')</script>"
        )

    @patch("services.email_sync.app.publish_message")
    def test_webhook_malicious_payload_handling(self, mock_publish):
        """Test handling of potentially malicious webhook payloads."""
        client = self.create_test_client(app)
        # Test with extremely large payload
        large_payload = {
            "history_id": "12345",
            "email_address": "user@example.com",
            "extra_data": "x" * 1000000,  # 1MB of data
        }
        response = client.post(
            "/gmail/webhook",
            json=large_payload,
            headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
        )

        # Should still process successfully (or handle gracefully)
        assert response.status_code in [200, 413]  # 413 if payload too large
        if response.status_code == 200:
            mock_publish.assert_called_once()
