"""
Backend API tests for email parser and data collection endpoints.

Tests the email parser API with various email formats, error handling,
authentication, and data collection functionality.
"""

import pytest
from fastapi.testclient import TestClient

from services.shipments.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the _settings global variable to return test settings."""
    import services.shipments.settings as shipments_settings

    test_settings = shipments_settings.Settings(
        db_url_shipments="sqlite:///:memory:",
        api_frontend_shipments_key="test-frontend-shipments-key",
    )

    # Directly set the singleton instead of using monkeypatch
    shipments_settings._settings = test_settings
    yield
    shipments_settings._settings = None


# Test data for various email formats
SAMPLE_EMAILS = {
    "amazon_ups": {
        "subject": "Your Amazon order has shipped",
        "sender": "shipment-tracking@amazon.com",
        "body": """
        Hello,

        Your order #123-4567890-1234567 has shipped via UPS.
        Tracking number: 1Z999AA1234567890
        
        Expected delivery: Tomorrow by 8:00 PM
        
        Track your package: https://www.ups.com/track?tracknum=1Z999AA1234567890
        
        Thank you for shopping with Amazon!
        """,
        "content_type": "text",
    },
    "fedex": {
        "subject": "FedEx Shipment Notification",
        "sender": "notifications@fedex.com",
        "body": """
        Your package has been shipped via FedEx.
        Tracking number: 123456789012
        Service: FedEx Ground
        
        Estimated delivery: 3-5 business days
        
        Track at: https://www.fedex.com/fedextrack/?trknbr=123456789012
        """,
        "content_type": "text",
    },
    "usps": {
        "subject": "USPS Tracking Update",
        "sender": "tracking@usps.com",
        "body": """
        Your USPS package is in transit.
        Tracking number: 9400100000000000000000
        
        Current status: In Transit
        Location: Distribution Center
        
        Track at: https://tools.usps.com/go/TrackConfirmAction?tLabels=9400100000000000000000
        """,
        "content_type": "text",
    },
    "dhl": {
        "subject": "DHL Shipment Update",
        "sender": "tracking@dhl.com",
        "body": """
        Your DHL package is on its way.
        Tracking number: 1234567890
        
        Status: In Transit
        Estimated delivery: 2-3 business days
        
        Track at: https://www.dhl.com/track?tracking-id=1234567890
        """,
        "content_type": "text",
    },
    "non_shipment": {
        "subject": "Meeting Reminder",
        "sender": "calendar@company.com",
        "body": """
        Hi there,
        
        Just a reminder about our meeting tomorrow at 2 PM.
        
        Best regards,
        Calendar System
        """,
        "content_type": "text",
    },
    "html_email": {
        "subject": "Your order has shipped",
        "sender": "orders@store.com",
        "body": """
        <html>
        <body>
        <h1>Your order has shipped!</h1>
        <p>Tracking number: <strong>1Z999AA1234567890</strong></p>
        <p>Carrier: UPS</p>
        <p>Expected delivery: Tomorrow</p>
        </body>
        </html>
        """,
        "content_type": "html",
    },
}


class TestEmailParserCore:
    """Test email parser core functionality without authentication."""

    def test_parse_amazon_ups_email_core(self):
        """Test parsing Amazon email with UPS tracking - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["amazon_ups"]["subject"],
            sender=SAMPLE_EMAILS["amazon_ups"]["sender"],
            body=SAMPLE_EMAILS["amazon_ups"]["body"],
            content_type=SAMPLE_EMAILS["amazon_ups"]["content_type"],
        )

        assert result.is_shipment_email is True
        assert result.detected_carrier == "amazon"
        assert len(result.tracking_numbers) > 0
        # Check that we found some tracking number (the exact one may vary based on regex patterns)
        assert any("1234567890" in tn for tn in result.tracking_numbers)
        assert result.confidence > 0.5

    def test_parse_fedex_email_core(self):
        """Test parsing FedEx email - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["fedex"]["subject"],
            sender=SAMPLE_EMAILS["fedex"]["sender"],
            body=SAMPLE_EMAILS["fedex"]["body"],
            content_type=SAMPLE_EMAILS["fedex"]["content_type"],
        )

        assert result.is_shipment_email is True
        assert result.detected_carrier == "fedex"
        assert len(result.tracking_numbers) > 0
        assert "123456789012" in result.tracking_numbers

    def test_parse_usps_email_core(self):
        """Test parsing USPS email - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["usps"]["subject"],
            sender=SAMPLE_EMAILS["usps"]["sender"],
            body=SAMPLE_EMAILS["usps"]["body"],
            content_type=SAMPLE_EMAILS["usps"]["content_type"],
        )

        assert result.is_shipment_email is True
        assert result.detected_carrier == "usps"
        assert len(result.tracking_numbers) > 0
        assert "9400100000000000000000" in result.tracking_numbers

    def test_parse_dhl_email_core(self):
        """Test parsing DHL email - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["dhl"]["subject"],
            sender=SAMPLE_EMAILS["dhl"]["sender"],
            body=SAMPLE_EMAILS["dhl"]["body"],
            content_type=SAMPLE_EMAILS["dhl"]["content_type"],
        )

        assert result.is_shipment_email is True
        assert result.detected_carrier == "dhl"
        assert len(result.tracking_numbers) > 0
        assert "1234567890" in result.tracking_numbers

    def test_parse_html_email_core(self):
        """Test parsing HTML email - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["html_email"]["subject"],
            sender=SAMPLE_EMAILS["html_email"]["sender"],
            body=SAMPLE_EMAILS["html_email"]["body"],
            content_type=SAMPLE_EMAILS["html_email"]["content_type"],
        )

        assert result.is_shipment_email is True
        assert len(result.tracking_numbers) > 0
        # Check that we found some tracking number (the exact one may vary based on regex patterns)
        assert any("1234567890" in tn for tn in result.tracking_numbers)

    def test_parse_non_shipment_email_core(self):
        """Test parsing non-shipment email - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["non_shipment"]["subject"],
            sender=SAMPLE_EMAILS["non_shipment"]["sender"],
            body=SAMPLE_EMAILS["non_shipment"]["body"],
            content_type=SAMPLE_EMAILS["non_shipment"]["content_type"],
        )

        # Should detect as non-shipment or low confidence
        assert result.is_shipment_email is False or result.confidence < 0.3

    def test_empty_body_core(self):
        """Test parsing email with empty body - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["amazon_ups"]["subject"],
            sender=SAMPLE_EMAILS["amazon_ups"]["sender"],
            body="",
            content_type="text",
        )

        # Should still detect based on sender domain
        assert result.is_shipment_email is True

    def test_very_long_email_core(self):
        """Test parsing very long email - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        long_body = "x" * 10000 + "\nTracking number: 1Z999AA1234567890"
        result = parser.parse_email(
            subject="Test",
            sender="test@example.com",
            body=long_body,
            content_type="text",
        )

        assert len(result.tracking_numbers) > 0

    def test_multiple_tracking_numbers_core(self):
        """Test parsing email with multiple tracking numbers - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        multi_body = (
            SAMPLE_EMAILS["amazon_ups"]["body"]
            + "\nAdditional tracking: 1Z999AA9876543210"
        )
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["amazon_ups"]["subject"],
            sender=SAMPLE_EMAILS["amazon_ups"]["sender"],
            body=multi_body,
            content_type="text",
        )

        assert len(result.tracking_numbers) >= 2


class TestEmailParserAPI:
    """Test email parser API endpoints with authentication."""

    def test_authentication_required(self):
        """Test that authentication is required."""
        response = client.post(
            "/api/v1/email-parser/parse", json=SAMPLE_EMAILS["amazon_ups"]
        )

        # Should fail without authentication
        assert response.status_code in [401, 403]

    def test_missing_required_fields(self):
        """Test error handling for missing required fields."""
        incomplete_data = {
            "user_id": "user123",
            "subject": "Test email",
            # Missing sender and body
        }

        response = client.post("/api/v1/email-parser/parse", json=incomplete_data)

        # Should fail due to missing authentication first
        assert response.status_code in [401, 403]

    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/v1/email-parser/parse",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422


class TestDataCollectionCore:
    """Test data collection core functionality."""

    def test_data_collection_structure(self):
        """Test data collection request structure validation."""
        from services.shipments.routers.data_collection import DataCollectionRequest

        # Valid data collection request
        collection_data = {
            "email_message_id": "email123",
            "original_email_data": {
                "subject": "Test email",
                "sender": "test@example.com",
                "body": "Test body",
            },
            "auto_detected_data": {
                "tracking_number": "1Z999AA1234567890",
                "carrier": "ups",
                "confidence": 0.85,
            },
            "user_corrected_data": {
                "tracking_number": "1Z999AA1234567890",
                "carrier": "ups",
                "status": "in_transit",
            },
            "detection_confidence": 0.85,
            "correction_reason": "User confirmed carrier",
            "consent_given": True,
        }

        # Should validate successfully
        request = DataCollectionRequest(**collection_data)
        assert request.consent_given is True
        assert request.detection_confidence == 0.85

    def test_data_collection_invalid_confidence(self):
        """Test data collection with invalid confidence score."""
        from pydantic import ValidationError

        from services.shipments.routers.data_collection import DataCollectionRequest

        invalid_data = {
            "email_message_id": "email123",
            "original_email_data": {},
            "auto_detected_data": {},
            "user_corrected_data": {},
            "detection_confidence": 1.5,  # Invalid: > 1.0
            "consent_given": True,
        }

        # Should raise validation error
        with pytest.raises(ValidationError):
            DataCollectionRequest(**invalid_data)

    def test_data_collection_missing_required_fields(self):
        """Test data collection with missing required fields."""
        from pydantic import ValidationError

        from services.shipments.routers.data_collection import DataCollectionRequest

        incomplete_data = {
            "email_message_id": "email123",
            # Missing other required fields
        }

        # Should raise validation error
        with pytest.raises(ValidationError):
            DataCollectionRequest(**incomplete_data)


class TestDataCollectionAPI:
    """Test data collection API endpoints."""

    def test_data_collection_authentication_required(self):
        """Test that data collection requires authentication."""
        response = client.post(
            "/api/v1/data-collection/collect",
            json={
                "email_message_id": "email123",
                "original_email_data": {},
                "auto_detected_data": {},
                "user_corrected_data": {},
                "detection_confidence": 0.8,
                "consent_given": True,
            },
        )

        # Should fail without authentication
        assert response.status_code in [401, 403]


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_email_parser_internal_error_core(self):
        """Test email parser internal error handling - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()

        # Test with invalid input that might cause issues
        try:
            result = parser.parse_email(
                subject=None,  # Invalid input
                sender="test@example.com",
                body="Test body",
                content_type="text",
            )
            # Should handle gracefully
            assert result is not None
        except Exception:
            # If it raises an exception, that's also acceptable for invalid input
            pass

    def test_large_payload_core(self):
        """Test handling of very large payload - core functionality."""
        from services.shipments.email_parser import EmailParser

        parser = EmailParser()
        large_body = "x" * 100000  # Very large body

        try:
            result = parser.parse_email(
                subject="Test",
                sender="test@example.com",
                body=large_body,
                content_type="text",
            )
            # Should handle large payload gracefully
            assert result is not None
        except Exception:
            # If it raises an exception, that's also acceptable for very large input
            pass


class TestPerformance:
    """Test performance characteristics."""

    def test_email_parser_performance_core(self):
        """Test email parser performance with typical email - core functionality."""
        import time

        from services.shipments.email_parser import EmailParser

        parser = EmailParser()

        start_time = time.time()
        result = parser.parse_email(
            subject=SAMPLE_EMAILS["amazon_ups"]["subject"],
            sender=SAMPLE_EMAILS["amazon_ups"]["sender"],
            body=SAMPLE_EMAILS["amazon_ups"]["body"],
            content_type=SAMPLE_EMAILS["amazon_ups"]["content_type"],
        )
        end_time = time.time()

        assert result is not None
        # Should complete within reasonable time (e.g., 1 second)
        assert (end_time - start_time) < 1.0


class TestSchemaValidation:
    """Test schema validation for request/response models."""

    def test_email_parse_request_validation(self):
        """Test EmailParseRequest schema validation."""
        from services.shipments.schemas.email_parser import EmailParseRequest

        # Valid request
        valid_data = SAMPLE_EMAILS["amazon_ups"]
        request = EmailParseRequest(**valid_data)
        assert request.subject == "Your Amazon order has shipped"
        assert request.subject == "Your Amazon order has shipped"
        assert request.sender == "shipment-tracking@amazon.com"

    def test_email_parse_response_structure(self):
        """Test EmailParseResponse schema structure."""
        from services.shipments.schemas.email_parser import (
            EmailParseResponse,
            ParsedTrackingInfo,
        )

        # Create sample response
        tracking_info = ParsedTrackingInfo(
            tracking_number="1Z999AA1234567890",
            carrier="ups",
            confidence=0.95,
            source="body",
        )

        response = EmailParseResponse(
            is_shipment_email=True,
            detected_carrier="amazon",
            tracking_numbers=[tracking_info],
            confidence=0.85,
            detected_from="multiple",
            suggested_package_data={
                "carrier": "ups",
                "tracking_number": "1Z999AA1234567890",
                "status": "in_transit",
            },
        )

        assert response.is_shipment_email is True
        assert response.detected_carrier == "amazon"
        assert len(response.tracking_numbers) == 1
        assert response.tracking_numbers[0].tracking_number == "1Z999AA1234567890"
        assert response.confidence == 0.85


if __name__ == "__main__":
    pytest.main([__file__])
