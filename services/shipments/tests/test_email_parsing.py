"""
Test cases for shipments service email parsing functionality.

This module tests the email parsing logic for extracting tracking information
from shipping notification emails from various carriers.
"""

from services.shipments.test_base import BaseShipmentsTest
from services.shipments.tests.test_data.email_samples import (
    get_all_samples,
    get_edge_cases,
    get_samples_by_carrier,
)


class TestEmailParsing(BaseShipmentsTest):
    """Test email parsing functionality for shipping notifications."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        # Import the email parser module
        from services.shipments.email_parser import EmailParser

        self.parser = EmailParser()

    def test_ups_email_parsing(self):
        """Test parsing of UPS shipping notification emails."""
        ups_samples = get_samples_by_carrier("UPS")

        for sample in ups_samples:
            parsed_data = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

            # Assertions for expected parsing results
            assert parsed_data.carrier == sample.expected_carrier
            assert parsed_data.tracking_number == sample.expected_tracking_number
            assert parsed_data.order_number == sample.expected_order_number
            assert parsed_data.tracking_link == sample.expected_tracking_link
            assert parsed_data.recipient_name == sample.expected_recipient
            assert parsed_data.estimated_delivery == sample.expected_estimated_delivery
            assert parsed_data.status == sample.expected_status
            assert parsed_data.is_valid_tracking is True
            assert parsed_data.confidence_score > 0.5

    def test_fedex_email_parsing(self):
        """Test parsing of FedEx shipping notification emails."""
        fedex_samples = get_samples_by_carrier("FEDEX")

        for sample in fedex_samples:
            parsed_data = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

            # Assertions for expected parsing results
            assert parsed_data.carrier == sample.expected_carrier
            assert parsed_data.tracking_number == sample.expected_tracking_number
            assert parsed_data.order_number == sample.expected_order_number
            assert parsed_data.tracking_link == sample.expected_tracking_link
            assert parsed_data.recipient_name == sample.expected_recipient
            assert parsed_data.estimated_delivery == sample.expected_estimated_delivery
            assert parsed_data.status == sample.expected_status
            assert parsed_data.is_valid_tracking is True
            assert parsed_data.confidence_score > 0.5

    def test_usps_email_parsing(self):
        """Test parsing of USPS shipping notification emails."""
        usps_samples = get_samples_by_carrier("USPS")

        for sample in usps_samples:
            parsed_data = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

            # Assertions for expected parsing results
            assert parsed_data.carrier == sample.expected_carrier
            assert parsed_data.tracking_number == sample.expected_tracking_number
            assert parsed_data.order_number == sample.expected_order_number
            assert parsed_data.tracking_link == sample.expected_tracking_link
            assert parsed_data.recipient_name == sample.expected_recipient
            assert parsed_data.is_valid_tracking is True
            assert parsed_data.confidence_score > 0.5

    def test_amazon_email_parsing(self):
        """Test parsing of Amazon shipping notification emails."""
        amazon_samples = get_samples_by_carrier("AMAZON")

        for sample in amazon_samples:
            parsed_data = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

            # Assertions for expected parsing results
            assert parsed_data.carrier == sample.expected_carrier
            assert parsed_data.tracking_number == sample.expected_tracking_number
            assert parsed_data.order_number == sample.expected_order_number
            assert parsed_data.tracking_link == sample.expected_tracking_link
            assert parsed_data.recipient_name == sample.expected_recipient
            assert parsed_data.is_valid_tracking is True
            assert parsed_data.confidence_score > 0.5

    def test_amazon_tracking_link_extraction(self):
        """Test that Amazon tracking links are extracted from actual email content."""
        # Test case with actual Amazon order details link in email body
        subject = "Ordered: ETENWOLF T300 Plus Tire"
        sender = "shipment-tracking@amazon.com"
        body = """
        <html>
        <body>
        <p>Your order has been confirmed.</p>
        <p>Order #112-2389056-9870626</p>
        <p>Track your order: <a href="https://www.amazon.com/gp/css/order-details?orderID=3D112-2389056-9870626&r=">Click here</a></p>
        <p>Estimated delivery: Monday</p>
        </body>
        </html>
        """

        parsed_data = self.parser.parse_email(subject, sender, body)

        # Verify the actual link from the email is extracted
        assert parsed_data.carrier == "AMAZON"
        assert parsed_data.order_number == "112-2389056-9870626"
        # The URL cleaning should handle the HTML tag artifacts
        assert (
            "https://www.amazon.com/gp/css/order-details?orderID=112-2389056-9870626"
            in parsed_data.tracking_link
        )
        assert (
            parsed_data.tracking_number == ""
        )  # Amazon doesn't provide traditional tracking numbers
        assert parsed_data.is_valid_tracking is False  # No traditional tracking number

        # Test URL cleaning functionality
        test_url = "https://www.amazon.com/gp/css/order-details?orderID=3D112-2389056-9870626&r="
        cleaned_url = self.parser._clean_url(test_url)
        assert (
            cleaned_url
            == "https://www.amazon.com/gp/css/order-details?orderID=112-2389056-9870626&r"
        )

        # Test that link extraction works when carrier is detected as AMAZON
        # (The link extraction doesn't work with UNKNOWN carrier because patterns are carrier-specific)
        tracking_link = self.parser._extract_tracking_link(
            body, "AMAZON", "", "112-2389056-9870626"
        )
        # The link extraction should work when carrier is AMAZON
        assert tracking_link is not None
        assert (
            "https://www.amazon.com/gp/css/order-details?orderID=112-2389056-9870626"
            in tracking_link
        )

    def test_dhl_email_parsing(self):
        """Test parsing of DHL shipping notification emails."""
        dhl_samples = get_samples_by_carrier("DHL")

        for sample in dhl_samples:
            parsed_data = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

            # Assertions for expected parsing results
            assert parsed_data.carrier == sample.expected_carrier
            assert parsed_data.tracking_number == sample.expected_tracking_number
            assert parsed_data.order_number == sample.expected_order_number
            assert parsed_data.tracking_link == sample.expected_tracking_link
            assert parsed_data.recipient_name == sample.expected_recipient
            assert parsed_data.is_valid_tracking is True
            assert parsed_data.confidence_score > 0.5

    def test_edge_cases(self):
        """Test parsing of edge cases and error scenarios."""
        edge_cases = get_edge_cases()

        for sample in edge_cases:
            parsed_data = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

            # Test different edge case scenarios
            if "multiple" in sample.subject.lower():
                # Should handle multiple tracking numbers
                multiple_tracking = self.parser.parse_multiple_tracking_numbers(
                    sample.body
                )
                assert len(multiple_tracking) > 1
            elif "no tracking" in sample.subject.lower():
                # Should handle emails without tracking numbers
                assert parsed_data.tracking_number == ""
                assert parsed_data.carrier == "UNKNOWN"
            elif "invalid" in sample.subject.lower():
                # Should handle invalid tracking number formats
                assert parsed_data.is_valid_tracking is False

    def test_tracking_number_validation(self):
        """Test validation of tracking number formats."""
        test_cases = [
            ("1Z999AA12345678901", "UPS", True),
            ("123456789012", "FEDEX", True),
            ("9400100000000000000000", "USPS", True),
            ("1234567890", "DHL", True),
            ("INVALID-TRACKING-123", "UNKNOWN", False),
            ("", "UNKNOWN", False),
        ]

        for tracking_number, expected_carrier, is_valid in test_cases:
            result = self.parser._validate_tracking_number(
                tracking_number, expected_carrier
            )
            assert result == is_valid

    def test_carrier_detection(self):
        """Test carrier detection from email content."""
        test_cases = [
            ("noreply@ups.com", "UPS"),
            ("fedex@fedex.com", "FEDEX"),
            ("USPS@usps.com", "USPS"),
            ("shipment-tracking@amazon.com", "AMAZON"),
            ("dhl@dhl.com", "DHL"),
            ("unknown@example.com", "UNKNOWN"),
        ]

        for sender, expected_carrier in test_cases:
            detected_carrier = self.parser._detect_carrier(
                "Test subject", sender, "Test body"
            )
            assert detected_carrier == expected_carrier

    def test_order_number_extraction(self):
        """Test extraction of order numbers from email content."""
        test_cases = [
            ("Order #114-1234567-8901234", "114-1234567-8901234"),
            ("Order Number: ORD-2024-001234", "ORD-2024-001234"),
            ("Order: FED-2024-567890", "FED-2024-567890"),
            ("No order number here", None),
        ]

        for text, expected_order in test_cases:
            extracted_order = self.parser._extract_order_number(text)
            assert extracted_order == expected_order

    def test_tracking_link_extraction(self):
        """Test extraction of tracking links from email content."""
        test_cases = [
            (
                "Track here: https://www.ups.com/track?tracknum=1Z999AA12345678901",
                "https://www.ups.com/track?tracknum=1Z999AA12345678901",
            ),
            (
                "https://www.fedex.com/fedextrack/?trknbr=123456789012",
                "https://www.fedex.com/fedextrack/?trknbr=123456789012",
            ),
            ("No link here", None),
        ]

        for text, expected_link in test_cases:
            if "fedex" in text.lower():
                extracted_link = self.parser._extract_tracking_link(
                    text, "FEDEX", "123456789012"
                )
            elif "no link" in text.lower():
                extracted_link = self.parser._extract_tracking_link(text, "UNKNOWN", "")
            else:
                extracted_link = self.parser._extract_tracking_link(
                    text, "UPS", "1Z999AA12345678901"
                )
            assert extracted_link == expected_link

    def test_recipient_extraction(self):
        """Test extraction of recipient information from email content."""
        test_cases = [
            ("Recipient: John Doe", "John Doe"),
            ("To: Jane Smith", "Jane Smith"),
            ("- Recipient: Bob Johnson", "Bob Johnson"),
            ("No recipient info", None),
        ]

        for text, expected_recipient in test_cases:
            extracted_recipient = self.parser._extract_recipient_name(text)
            assert extracted_recipient == expected_recipient

    def test_delivery_date_extraction(self):
        """Test extraction of delivery dates from email content."""
        test_cases = [
            ("Estimated Delivery: December 15, 2024", "2024-12-15"),
            ("Expected delivery: Dec 18, 2024 by 8:00 PM", "2024-12-18"),
            ("Delivery: Today by 8:00 PM", None),  # Should handle relative dates
            ("No date info", None),
        ]

        for text, expected_date in test_cases:
            extracted_date = self.parser._extract_delivery_date(text)
            assert extracted_date == expected_date

    def test_email_parsing_integration(self):
        """Test complete email parsing integration."""
        all_samples = get_all_samples()

        for sample in all_samples[:5]:  # Test first 5 samples
            parsed_data = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

            # Verify all expected fields are extracted
            assert parsed_data.carrier == sample.expected_carrier
            assert parsed_data.tracking_number == sample.expected_tracking_number
            assert parsed_data.order_number == sample.expected_order_number
            assert parsed_data.tracking_link == sample.expected_tracking_link
            assert parsed_data.recipient_name == sample.expected_recipient
            assert parsed_data.estimated_delivery == sample.expected_estimated_delivery
            assert parsed_data.status == sample.expected_status

    def test_error_handling(self):
        """Test error handling in email parsing."""
        test_cases = [
            ("", "", ""),  # Empty email
            (
                "Subject",
                "Sender",
                "Body with invalid characters: \x00\x01",
            ),  # Invalid characters
        ]

        for subject, sender, body in test_cases:
            try:
                parsed_data = self.parser.parse_email(subject, sender, body)
                # Should not raise exception, but return empty/invalid result
                assert parsed_data is not None
                assert parsed_data.carrier == "UNKNOWN"
            except Exception as e:
                # Should handle gracefully
                assert isinstance(e, (ValueError, TypeError))

    def test_performance(self):
        """Test performance of email parsing."""
        import time

        all_samples = get_all_samples()
        start_time = time.time()

        for sample in all_samples:
            _ = self.parser.parse_email(
                subject=sample.subject, sender=sample.sender, body=sample.body
            )

        end_time = time.time()
        processing_time = end_time - start_time

        # Should process all samples in reasonable time (e.g., < 1 second)
        assert processing_time < 1.0

        # Should process each email in reasonable time (e.g., < 10ms)
        avg_time_per_email = processing_time / len(all_samples)
        assert avg_time_per_email < 0.01

    def test_amazon_shipment_id_extraction(self):
        """Test Amazon shipment ID extraction from tracking URLs."""
        # Test Amazon email with shipment ID in URL
        subject = 'Shipped: "Test Product"'
        sender = "shipment-tracking@amazon.com"
        body = """
        Your package was shipped!
        Order # 112-7543819-2960218
        Track package: https://www.amazon.com/progress-tracker/package?orderId=112-7543819-2960218&shipmentId=DBl82xhFM&vt=NOTIFICATIONS
        """

        parsed_data = self.parser.parse_email(subject, sender, body)

        # Should extract Amazon shipment ID as tracking number
        assert parsed_data.carrier == "AMAZON"
        assert parsed_data.tracking_number == "DBl82xhFM"
        assert parsed_data.order_number == "112-7543819-2960218"
        assert parsed_data.is_valid_tracking is True
        assert parsed_data.confidence_score > 0.7

    def test_llm_decision_framework(self):
        """Test LLM decision framework for complex emails."""
        # Test simple email (should not use LLM)
        simple_subject = "UPS Update: Package Shipped"
        simple_sender = "noreply@ups.com"
        simple_body = "Your package 1Z999AA12345678901 has been shipped!"

        simple_parsed = self.parser.parse_email(
            simple_subject, simple_sender, simple_body
        )
        should_use_llm_simple = self.parser._should_use_llm(
            simple_subject, simple_sender, simple_body, simple_parsed
        )

        assert should_use_llm_simple is False

        # Test complex email (should use LLM)
        complex_subject = "Order Update"
        complex_sender = "unknown@retailer.com"
        complex_body = """
        <html>
        <head><style>body { font-family: Arial; }</style></head>
        <body>
        <table><tr><td>Your order has multiple tracking numbers: 1Z999AA12345678901 and 1Z999AA12345678902</td></tr></table>
        </body>
        </html>
        """

        complex_parsed = self.parser.parse_email(
            complex_subject, complex_sender, complex_body
        )
        should_use_llm_complex = self.parser._should_use_llm(
            complex_subject, complex_sender, complex_body, complex_parsed
        )

        assert should_use_llm_complex is True

    def test_complex_format_detection(self):
        """Test complex format detection for LLM decision making."""
        # Test simple format
        simple_body = "Your package has been shipped. Tracking: 1Z999AA12345678901"
        is_complex_simple = self.parser._has_complex_format(simple_body)
        assert is_complex_simple is False

        # Test complex format with CSS
        complex_body = """
        <html>
        <head>
        <style>
        body { font-family: Arial, sans-serif; color: #333; }
        .tracking { background: #f0f0f0; padding: 10px; }
        </style>
        </head>
        <body>
        <div class="tracking">Your package has been shipped.</div>
        </body>
        </html>
        """
        is_complex_css = self.parser._has_complex_format(complex_body)
        assert is_complex_css is True

        # Test complex format with scripts
        script_body = """
        <html>
        <head><script>console.log('test');</script></head>
        <body>Your package has been shipped.</body>
        </html>
        """
        is_complex_script = self.parser._has_complex_format(script_body)
        assert is_complex_script is True

        # Test complex format with multiple tables
        table_body = """
        <html>
        <body>
        <table><tr><td>Header</td></tr></table>
        <table><tr><td>Content</td></tr></table>
        <table><tr><td>Footer</td></tr></table>
        <table><tr><td>Extra</td></tr></table>
        </body>
        </html>
        """
        is_complex_tables = self.parser._has_complex_format(table_body)
        assert is_complex_tables is True

    def test_parse_with_llm_fallback(self):
        """Test the parse_with_llm_fallback method."""
        # Test with simple email
        subject = "UPS Update: Package Shipped"
        sender = "noreply@ups.com"
        body = "Your package 1Z999AA12345678901 has been shipped!"

        result = self.parser.parse_with_llm_fallback(subject, sender, body)

        assert result.carrier == "UPS"
        assert result.tracking_number == "1Z999AA12345678901"
        assert result.is_valid_tracking is True

    def test_enhanced_false_positive_filtering(self):
        """Test enhanced false positive filtering for tracking numbers."""
        # Test that common false positives are filtered out
        false_positives = [
            "content",
            "important",
            "font",
            "style",
            "script",
            "css",
            "background",
            "color",
            "border",
            "margin",
            "padding",
            "recipient",
            "valued",
            "dear",
            "hello",
            "shipment",
            "december",
        ]

        for false_positive in false_positives:
            is_false = self.parser._is_common_false_positive(false_positive)
            assert is_false, f"'{false_positive}' should be flagged as false positive"

        # Test that valid tracking numbers are not filtered out
        valid_tracking = [
            "1Z999AA12345678901",  # UPS
            "123456789012",  # FedEx
            "9400100000000000000000",  # USPS
            "ABC123XYZ",  # Amazon shipment ID
        ]

        for tracking in valid_tracking:
            is_false = self.parser._is_common_false_positive(tracking)
            assert not is_false, f"'{tracking}' should not be flagged as false positive"

    def test_status_extraction(self):
        """Test extraction of shipping status from email content."""
        # Test shipped status
        shipped_subject = "Your package has been shipped"
        shipped_body = "Your package has been shipped and is on its way."
        parsed_data = self.parser.parse_email(
            shipped_subject, "test@example.com", shipped_body
        )
        assert parsed_data.status == "Shipped"

        # Test in transit status
        transit_subject = "Package Update"
        transit_body = "Your package is in transit and on its way to you."
        parsed_data = self.parser.parse_email(
            transit_subject, "test@example.com", transit_body
        )
        assert parsed_data.status == "In Transit"

        # Test delivered status
        delivered_subject = "Package Delivered"
        delivered_body = "Your package has been successfully delivered."
        parsed_data = self.parser.parse_email(
            delivered_subject, "test@example.com", delivered_body
        )
        assert parsed_data.status == "Delivered"

        # Test out for delivery status
        out_for_delivery_subject = "Out for Delivery"
        out_for_delivery_body = "Your package is out for delivery today."
        parsed_data = self.parser.parse_email(
            out_for_delivery_subject, "test@example.com", out_for_delivery_body
        )
        assert parsed_data.status == "Out For Delivery"

        # Test exception status
        exception_subject = "Delivery Exception"
        exception_body = "There was a delivery exception with your package."
        parsed_data = self.parser.parse_email(
            exception_subject, "test@example.com", exception_body
        )
        assert parsed_data.status == "Exception"

        # Test pending status
        pending_subject = "Order Pending"
        pending_body = "Your order is pending and being processed."
        parsed_data = self.parser.parse_email(
            pending_subject, "test@example.com", pending_body
        )
        assert parsed_data.status == "Pending"

        # Test no status found
        no_status_subject = "Order Confirmation"
        no_status_body = "Thank you for your order."
        parsed_data = self.parser.parse_email(
            no_status_subject, "test@example.com", no_status_body
        )
        assert parsed_data.status is None


class TestEmailParserIntegration(BaseShipmentsTest):
    """Integration tests for email parser with database operations."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        from services.shipments.email_parser import EmailParser

        self.parser = EmailParser()

    def test_create_package_from_email(self):
        """Test creating a package record from parsed email data."""
        sample = get_samples_by_carrier("UPS")[0]

        # Parse email
        parsed_data = self.parser.parse_email(
            subject=sample.subject, sender=sample.sender, body=sample.body
        )

        # Verify parsed data matches expected values
        assert parsed_data.tracking_number == sample.expected_tracking_number
        assert parsed_data.carrier == sample.expected_carrier
        assert parsed_data.order_number == sample.expected_order_number
        assert parsed_data.is_valid_tracking is True
        assert parsed_data.confidence_score > 0.5

    def test_duplicate_tracking_handling(self):
        """Test handling of duplicate tracking numbers."""
        sample = get_samples_by_carrier("UPS")[0]

        # Parse the same email twice
        parsed_data1 = self.parser.parse_email(
            subject=sample.subject, sender=sample.sender, body=sample.body
        )

        parsed_data2 = self.parser.parse_email(
            subject=sample.subject, sender=sample.sender, body=sample.body
        )

        # Should get identical results
        assert parsed_data1.tracking_number == parsed_data2.tracking_number
        assert parsed_data1.carrier == parsed_data2.carrier
        assert parsed_data1.order_number == parsed_data2.order_number
