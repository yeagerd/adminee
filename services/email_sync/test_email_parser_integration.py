"""
Integration tests for email parser service with sample email data.

These tests verify the email parser can handle real-world email content
and extract tracking numbers, Amazon status updates, and survey URLs correctly.
"""

import os
from unittest.mock import patch

from services.email_sync.email_parser_service import process_email
from services.email_sync.test_data import (
    create_mock_message,
)

# Set up test environment
os.environ["PYTHON_ENV"] = "test"


class TestEmailParserSampleDataIntegration:
    """Integration tests using sample email data."""

    def test_ups_tracking_email_integration(self):
        """Test parsing real UPS tracking email content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "UPS <noreply@ups.com>",
            "subject": "Your UPS package has been shipped",
            "body": "Your UPS package has been shipped. Tracking number: 1Z999AA1234567890E",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify tracking event was published
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            assert len(tracking_calls) == 1
            tracking_data = tracking_calls[0][0][1]
            assert tracking_data["carrier"] == "UPS"
            assert "1Z999AA1234567890" in tracking_data["tracking_number"]

    def test_fedex_tracking_email_integration(self):
        """Test parsing real FedEx tracking email content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "FedEx <noreply@fedex.com>",
            "subject": "Your FedEx package has been shipped",
            "body": "Your FedEx package has been shipped. Tracking number: 123456789012",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify tracking event was published
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            assert len(tracking_calls) == 1
            tracking_data = tracking_calls[0][0][1]
            assert tracking_data["carrier"] == "FedEx"
            assert "123456789012" in tracking_data["tracking_number"]

    def test_usps_tracking_email_integration(self):
        """Test parsing real USPS tracking email content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "USPS <noreply@usps.com>",
            "subject": "Your USPS package has been shipped",
            "body": "Your USPS package has been shipped. Tracking number: 9400100000000000000000",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify tracking event was published
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            assert len(tracking_calls) == 1
            tracking_data = tracking_calls[0][0][1]
            assert tracking_data["carrier"] == "USPS"
            assert len(tracking_data["tracking_number"]) >= 20

    def test_amazon_shipped_email_integration(self):
        """Test parsing real Amazon shipped email content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "Amazon <order-update@amazon.com>",
            "subject": "Your Amazon order has shipped",
            "body": "Your Amazon order has shipped! Order #123-4567890-1234567. View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify Amazon status event was published
            amazon_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "amazon-events"
            ]

            assert len(amazon_calls) == 1
            amazon_data = amazon_calls[0][0][1]
            assert amazon_data["status"] == "shipped"
            assert "amazon.com" in amazon_data["order_link"]

    def test_amazon_delivered_email_integration(self):
        """Test parsing real Amazon delivered email content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "Amazon <order-update@amazon.com>",
            "subject": "Your Amazon package has been delivered",
            "body": "Your Amazon package has been delivered! Order #123-4567890-1234567. View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify Amazon status event was published
            amazon_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "amazon-events"
            ]

            assert len(amazon_calls) == 1
            amazon_data = amazon_calls[0][0][1]
            assert amazon_data["status"] == "delivered"

    def test_amazon_delayed_email_integration(self):
        """Test parsing real Amazon delayed email content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "Amazon <order-update@amazon.com>",
            "subject": "Your Amazon package delivery has been delayed",
            "body": "Your Amazon package delivery has been delayed! Order #123-4567890-1234567. View your order: https://www.amazon.com/gp/your-account/order-details?orderID=123-4567890-1234567",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify Amazon status event was published
            amazon_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "amazon-events"
            ]

            assert len(amazon_calls) == 1
            amazon_data = amazon_calls[0][0][1]
            assert amazon_data["status"] == "delayed"

    def test_survey_response_email_integration(self):
        """Test parsing real survey response email content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "Survey Team <surveys@example.com>",
            "subject": "Please complete our survey",
            "body": "Thank you for your recent purchase! We'd love to hear your feedback. Please complete our survey: https://survey.ourapp.com/response/abc123",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify survey response event was published
            survey_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "survey-events"
            ]

            assert len(survey_calls) == 1
            survey_data = survey_calls[0][0][1]
            assert "survey.ourapp.com" in survey_data["survey_url"]

    def test_mixed_content_email_integration(self):
        """Test parsing email with multiple types of content."""
        # Create simple email data that process_email expects
        email_data = {
            "from": "Shipping Updates <shipping@example.com>",
            "subject": "Multiple packages shipped",
            "body": "Your orders have been shipped! Package 1: UPS Tracking: 1Z999AA1234567890E. Package 2: FedEx Tracking: 123456789012. Package 3: USPS Tracking: 9400111899223856928499",
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify multiple tracking events were published
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            # Should have multiple tracking events
            assert len(tracking_calls) >= 1

    def test_malformed_email_integration(self):
        """Test parsing malformed email content gracefully."""
        # Create a malformed email with missing required fields
        email_data = {
            "from": "test@example.com",
            "subject": "Test Email",
            # Missing body field
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed (should handle gracefully)
            assert message.acked
            assert not message.nacked

            # Verify no events were published for malformed content
            assert mock_publish.call_count == 0

    def test_email_with_multiple_tracking_numbers(self):
        """Test parsing email with multiple tracking numbers from different carriers."""
        # Create email with multiple tracking numbers
        email_content = """
        Your packages have been shipped!
        
        UPS Tracking: 1Z999AA1234567890
        FedEx Tracking: 123456789012
        USPS Tracking: 9400100000000000000000
        
        Thank you for your order.
        """

        email_data = {
            "from": "shipping@example.com",
            "subject": "Multiple packages shipped",
            "body": email_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify multiple tracking events were published
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            assert len(tracking_calls) == 3

            # Verify each carrier was detected
            carriers = [call[0][1]["carrier"] for call in tracking_calls]
            assert "UPS" in carriers
            assert "FedEx" in carriers
            assert "USPS" in carriers

    def test_email_with_amazon_status_and_tracking(self):
        """Test parsing email with both Amazon status and tracking number."""
        # Create email with Amazon status and tracking
        email_content = """
        Your Amazon order has been shipped!
        
        Tracking Number: 1Z999AA1234567890
        Expected Delivery: January 15, 2024
        
        View your order: https://amazon.com/orders/123456
        """

        email_data = {
            "from": "shipment-tracking@amazon.com",
            "subject": "Your Amazon order has shipped",
            "body": email_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify both Amazon status and tracking events were published
            amazon_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "amazon-events"
            ]
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            assert len(amazon_calls) == 1
            assert len(tracking_calls) == 1

            # Verify Amazon status data
            amazon_data = amazon_calls[0][0][1]
            assert amazon_data["status"] == "shipped"
            assert "amazon.com" in amazon_data["order_link"]

            # Verify tracking data
            tracking_data = tracking_calls[0][0][1]
            assert tracking_data["carrier"] == "UPS"
            assert "1Z999AA1234567890" in tracking_data["tracking_number"]

    def test_email_with_survey_and_tracking(self):
        """Test parsing email with both survey URL and tracking number."""
        # Create email with survey and tracking
        email_content = """
        Your package has been delivered!
        
        Tracking Number: 1Z999AA1234567890
        
        Please take our survey: https://survey.ourapp.com/response/abc123
        
        Thank you for your business.
        """

        email_data = {
            "from": "delivery@example.com",
            "subject": "Package delivered",
            "body": email_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify both survey and tracking events were published
            survey_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "survey-events"
            ]
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            assert len(survey_calls) == 1
            assert len(tracking_calls) == 1

            # Verify survey data
            survey_data = survey_calls[0][0][1]
            assert "survey.ourapp.com" in survey_data["survey_url"]

            # Verify tracking data
            tracking_data = tracking_calls[0][0][1]
            assert tracking_data["carrier"] == "UPS"
            assert "1Z999AA1234567890" in tracking_data["tracking_number"]

    def test_email_with_no_extractable_content(self):
        """Test parsing email with no extractable content."""
        # Create email with no tracking, Amazon status, or survey
        email_content = """
        Hello,
        
        This is just a regular email with no tracking numbers,
        Amazon status updates, or survey links.
        
        Best regards,
        John
        """

        email_data = {
            "from": "john@example.com",
            "subject": "Regular email",
            "body": email_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify no events were published
            assert mock_publish.call_count == 0

    def test_email_with_invalid_tracking_numbers(self):
        """Test parsing email with invalid tracking number formats."""
        # Create email with invalid tracking numbers
        email_content = """
        Your package has been shipped!
        
        Tracking Number: 12345 (invalid format)
        Another Tracking: ABC123 (also invalid)
        
        Thank you for your order.
        """

        email_data = {
            "from": "shipping@example.com",
            "subject": "Package shipped",
            "body": email_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify no tracking events were published (invalid formats)
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]

            assert len(tracking_calls) == 0

    def test_email_with_malformed_urls(self):
        """Test parsing email with malformed URLs."""
        # Create email with malformed URLs
        email_content = """
        Please take our survey:
        
        Invalid URL: not-a-url
        Another invalid: http://
        Malformed: https://survey.ourapp.com/response/
        
        Thank you.
        """

        email_data = {
            "from": "survey@example.com",
            "subject": "Survey request",
            "body": email_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify no survey events were published (malformed URLs)
            survey_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "survey-events"
            ]

            assert len(survey_calls) == 0

    def test_email_with_very_long_content(self):
        """Test parsing email with very long content."""
        # Create email with very long content
        long_content = "This is a very long email content. " * 1000
        long_content += "Tracking Number: 1Z999AA1234567890 " * 10
        long_content += "Survey: https://survey.ourapp.com/response/abc123 " * 10

        email_data = {
            "from": "long@example.com",
            "subject": "Very long email",
            "body": long_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify tracking and survey events were published
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]
            survey_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "survey-events"
            ]

            assert len(tracking_calls) >= 1
            assert len(survey_calls) >= 1

    def test_email_with_special_characters(self):
        """Test parsing email with special characters and encoding."""
        # Create email with special characters
        email_content = """
        Your package has been shipped! 🚚
        
        Tracking Number: 1Z999AA1234567890
        Expected Delivery: January 15, 2024 📦
        
        Please take our survey: https://survey.ourapp.com/response/abc123
        
        Thank you! 😊
        """

        email_data = {
            "from": "shipping@example.com",
            "subject": "Package shipped 🚚",
            "body": email_content,
        }

        # Create mock message
        message = create_mock_message(email_data)

        # Process the email
        with patch(
            "services.email_sync.email_parser_service.publish_message"
        ) as mock_publish:
            process_email(message)

            # Verify message was processed
            assert message.acked
            assert not message.nacked

            # Verify tracking and survey events were published
            tracking_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "package-tracker-events"
            ]
            survey_calls = [
                call
                for call in mock_publish.call_args_list
                if call[0][0] == "survey-events"
            ]

            assert len(tracking_calls) == 1
            assert len(survey_calls) == 1

            # Verify tracking data
            tracking_data = tracking_calls[0][0][1]
            assert tracking_data["carrier"] == "UPS"
            assert "1Z999AA1234567890" in tracking_data["tracking_number"]

            # Verify survey data
            survey_data = survey_calls[0][0][1]
            assert "survey.ourapp.com" in survey_data["survey_url"]
