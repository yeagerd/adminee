"""
Integration tests for webhook endpoints using realistic test data.

These tests verify that the webhook endpoints properly handle realistic
Gmail and Microsoft webhook payloads and publish appropriate messages
to pubsub topics.
"""

import os
import json
from unittest.mock import patch, MagicMock

import pytest

from services.email_sync.test_data import (
    gmail_webhook_payload,
    gmail_webhook_payload_with_multiple_emails,
    microsoft_webhook_payload,
    microsoft_webhook_payload_multiple_changes,
    get_all_test_emails,
    create_mock_message
)

# Set up test environment
os.environ["PYTHON_ENV"] = "test"
os.environ["GMAIL_WEBHOOK_SECRET"] = "test-gmail-webhook-secret"
os.environ["MICROSOFT_WEBHOOK_SECRET"] = "test-microsoft-webhook-secret"

from services.email_sync.app import app


class TestGmailWebhookIntegration:
    """Integration tests for Gmail webhook endpoint."""

    def test_gmail_webhook_with_realistic_payload(self):
        """Test Gmail webhook with realistic payload."""
        with patch("services.email_sync.app.app.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = gmail_webhook_payload()
                response = client.post(
                    "/gmail/webhook",
                    json=payload,
                    headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
                )
                
                assert response.status_code == 200
                assert response.json["status"] == "ok"
                
                # Verify message was published to gmail-notifications topic
                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[0][0] == "gmail-notifications"
                assert call_args[0][1]["history_id"] == "12345"
                assert call_args[0][1]["email_address"] == "user@example.com"

    def test_gmail_webhook_with_multiple_emails_payload(self):
        """Test Gmail webhook with payload that might trigger multiple email fetches."""
        with patch("services.email_sync.app.app.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = gmail_webhook_payload_with_multiple_emails()
                response = client.post(
                    "/gmail/webhook",
                    json=payload,
                    headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
                )
                
                assert response.status_code == 200
                assert response.json["status"] == "ok"
                
                # Verify message was published
                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[0][0] == "gmail-notifications"
                assert call_args[0][1]["history_id"] == "67890"

    def test_gmail_webhook_invalid_secret(self):
        """Test Gmail webhook with invalid secret."""
        with patch("services.email_sync.app.app.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = gmail_webhook_payload()
                response = client.post(
                    "/gmail/webhook",
                    json=payload,
                    headers={"X-Gmail-Webhook-Secret": "wrong-secret"},
                )
                
                assert response.status_code == 401
                mock_publish.assert_not_called()

    def test_gmail_webhook_missing_secret_header(self):
        """Test Gmail webhook with missing secret header."""
        with patch("services.email_sync.app.app.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = gmail_webhook_payload()
                response = client.post(
                    "/gmail/webhook",
                    json=payload,
                )
                
                assert response.status_code == 401
                mock_publish.assert_not_called()

    def test_gmail_webhook_invalid_payload_missing_history_id(self):
        """Test Gmail webhook with invalid payload missing history_id."""
        with patch("services.email_sync.app.app.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = {"email_address": "user@example.com"}  # Missing history_id
                response = client.post(
                    "/gmail/webhook",
                    json=payload,
                    headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
                )
                
                assert response.status_code == 400
                mock_publish.assert_not_called()

    def test_gmail_webhook_invalid_payload_missing_email_address(self):
        """Test Gmail webhook with invalid payload missing email_address."""
        with patch("services.email_sync.app.app.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = {"history_id": "12345"}  # Missing email_address
                response = client.post(
                    "/gmail/webhook",
                    json=payload,
                    headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
                )
                
                assert response.status_code == 400
                mock_publish.assert_not_called()

    def test_gmail_webhook_pubsub_failure(self):
        """Test Gmail webhook when pubsub publishing fails."""
        with patch("services.email_sync.app.app.publish_message", side_effect=Exception("pubsub error")) as mock_publish:
            with app.test_client() as client:
                payload = gmail_webhook_payload()
                response = client.post(
                    "/gmail/webhook",
                    json=payload,
                    headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
                )
                
                assert response.status_code == 503
                mock_publish.assert_called_once()


class TestMicrosoftWebhookIntegration:
    """Integration tests for Microsoft webhook endpoint."""

    def test_microsoft_webhook_with_realistic_payload(self):
        """Test Microsoft webhook with realistic payload."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload()
                response = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                
                assert response.status_code == 200
                assert response.json["status"] == "published"
                
                # Verify message was published to microsoft-notifications topic
                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[0][0] == "microsoft-notifications"
                assert "value" in call_args[0][1]
                assert len(call_args[0][1]["value"]) == 1

    def test_microsoft_webhook_with_multiple_changes(self):
        """Test Microsoft webhook with multiple email changes."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload_multiple_changes()
                response = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                
                assert response.status_code == 200
                assert response.json["status"] == "published"
                
                # Verify message was published
                mock_publish.assert_called_once()
                call_args = mock_publish.call_args
                assert call_args[0][0] == "microsoft-notifications"
                assert len(call_args[0][1]["value"]) == 2

    def test_microsoft_webhook_invalid_signature(self):
        """Test Microsoft webhook with invalid signature."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload()
                response = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "wrong-secret"},
                )
                
                assert response.status_code == 401
                mock_publish.assert_not_called()

    def test_microsoft_webhook_missing_signature_header(self):
        """Test Microsoft webhook with missing signature header."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload()
                response = client.post(
                    "/microsoft/webhook",
                    json=payload,
                )
                
                assert response.status_code == 401
                mock_publish.assert_not_called()

    def test_microsoft_webhook_invalid_payload_not_json(self):
        """Test Microsoft webhook with invalid non-JSON payload."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
                response = client.post(
                    "/microsoft/webhook",
                    data="not a json",
                    headers={
                        "X-Microsoft-Signature": "test-microsoft-webhook-secret",
                        "Content-Type": "application/json"
                    },
                )
                
                assert response.status_code == 400
                mock_publish.assert_not_called()

    def test_microsoft_webhook_invalid_payload_missing_value(self):
        """Test Microsoft webhook with invalid payload missing value field."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
                payload = {"invalid": "payload"}
                response = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                
                assert response.status_code == 400
                mock_publish.assert_not_called()

    def test_microsoft_webhook_pubsub_failure(self):
        """Test Microsoft webhook when pubsub publishing fails."""
        with patch("services.email_sync.microsoft_webhook.publish_message", side_effect=Exception("pubsub error")) as mock_publish:
            with app.test_client() as client:
                payload = microsoft_webhook_payload()
                response = client.post(
                    "/microsoft/webhook",
                    json=payload,
                    headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                )
                
                assert response.status_code == 400
                mock_publish.assert_called_once()


class TestWebhookEndToEnd:
    """End-to-end tests for webhook processing pipeline."""

    def test_gmail_webhook_to_email_processing_pipeline(self):
        """Test complete Gmail webhook to email processing pipeline."""
        with patch("services.email_sync.app.publish_message") as mock_publish:
            with app.test_client() as client:
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

    def test_microsoft_webhook_to_email_processing_pipeline(self):
        """Test complete Microsoft webhook to email processing pipeline."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
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

    def test_webhook_rate_limiting_simulation(self):
        """Test webhook handling under simulated load."""
        with patch("services.email_sync.app.publish_message") as mock_publish:
            with app.test_client() as client:
                # Send multiple Gmail webhooks rapidly
                for i in range(5):
                    payload = gmail_webhook_payload(history_id=str(i), email_address=f"user{i}@example.com")
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

    def test_webhook_error_recovery(self):
        """Test webhook error recovery scenarios."""
        with patch("services.email_sync.app.publish_message") as mock_publish:
            with app.test_client() as client:
                # First call fails, second succeeds
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


class TestWebhookDataValidation:
    """Tests for webhook data validation and sanitization."""

    def test_gmail_webhook_data_sanitization(self):
        """Test that Gmail webhook data is properly sanitized."""
        with patch("services.email_sync.app.publish_message") as mock_publish:
            with app.test_client() as client:
                # Test with various data types and edge cases
                test_cases = [
                    {"history_id": "12345", "email_address": "user@example.com"},
                    {"history_id": "67890", "email_address": "test.user+tag@domain.com"},
                    {"history_id": "abc123", "email_address": "user123@test-domain.org"},
                ]
                
                for payload in test_cases:
                    response = client.post(
                        "/gmail/webhook",
                        json=payload,
                        headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify published data matches input
                    call_args = mock_publish.call_args
                    published_data = call_args[0][1]
                    assert published_data["history_id"] == payload["history_id"]
                    assert published_data["email_address"] == payload["email_address"]

    def test_microsoft_webhook_data_sanitization(self):
        """Test that Microsoft webhook data is properly sanitized."""
        with patch("services.email_sync.microsoft_webhook.publish_message") as mock_publish:
            with app.test_client() as client:
                # Test with various change types and resource formats
                test_cases = [
                    microsoft_webhook_payload("created", "me/messages/1"),
                    microsoft_webhook_payload("updated", "me/messages/2"),
                    microsoft_webhook_payload("deleted", "me/messages/3"),
                ]
                
                for payload in test_cases:
                    response = client.post(
                        "/microsoft/webhook",
                        json=payload,
                        headers={"X-Microsoft-Signature": "test-microsoft-webhook-secret"},
                    )
                    
                    assert response.status_code == 200
                    
                    # Verify published data matches input
                    call_args = mock_publish.call_args
                    published_data = call_args[0][1]
                    assert published_data["value"][0]["changeType"] == payload["value"][0]["changeType"]
                    assert published_data["value"][0]["resource"] == payload["value"][0]["resource"]

    def test_webhook_malicious_payload_handling(self):
        """Test handling of potentially malicious webhook payloads."""
        with patch("services.email_sync.app.publish_message") as mock_publish:
            with app.test_client() as client:
                # Test with oversized payload
                oversized_payload = {
                    "history_id": "12345",
                    "email_address": "user@example.com",
                    "extra_data": "x" * 10000  # Very large payload
                }
                
                response = client.post(
                    "/gmail/webhook",
                    json=oversized_payload,
                    headers={"X-Gmail-Webhook-Secret": "test-gmail-webhook-secret"},
                )
                
                # Should still process valid payloads even with extra data
                assert response.status_code == 200
                mock_publish.assert_called_once()
                
                # Verify only expected fields are published
                call_args = mock_publish.call_args
                published_data = call_args[0][1]
                assert "history_id" in published_data
                assert "email_address" in published_data
                assert "extra_data" not in published_data  # Extra data should be filtered out 