"""
Unit tests for common validation utilities.

Tests comprehensive validation, sanitization, and security measures
including edge cases and malicious input attempts.
"""

import pytest

from services.common.validation import (
    ValidationError,
    check_sql_injection_patterns,
    sanitize_text_input,
    validate_email_address,
    validate_enum_value,
    validate_file_path,
    validate_json_safe_string,
    validate_pagination_params,
    validate_phone_number,
    validate_time_format,
    validate_timezone,
    validate_url,
)


class TestValidationUtilities:
    """Test cases for validation utility functions."""

    def test_sanitize_text_input_normal(self):
        """Test normal text sanitization."""
        result = sanitize_text_input("Hello World")
        assert result == "Hello World"

    def test_sanitize_text_input_html_removal(self):
        """Test HTML tag removal."""
        with pytest.raises(ValidationError, match="Text contains HTML tags or scripts"):
            sanitize_text_input("<script>alert('xss')</script>Hello")

    def test_sanitize_text_input_dangerous_chars(self):
        """Test dangerous character removal."""
        with pytest.raises(ValidationError, match="Text contains dangerous characters"):
            sanitize_text_input('Hello"World;test\'')

    def test_sanitize_text_input_max_length(self):
        """Test maximum length enforcement."""
        long_text = "a" * 200
        with pytest.raises(ValidationError) as exc_info:
            sanitize_text_input(long_text, max_length=100)
        assert "maximum length" in str(exc_info.value)

    def test_sanitize_text_input_malicious_patterns(self):
        """Test malicious pattern detection."""
        malicious_inputs = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "onclick=alert('xss')",
            "onload=malicious()",
        ]

        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError):
                sanitize_text_input(malicious_input)

    def test_validate_email_address_valid(self):
        """Test valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "user123@test-domain.org",
        ]

        for email in valid_emails:
            result = validate_email_address(email)
            assert result == email.lower()

    def test_validate_email_address_invalid(self):
        """Test invalid email addresses."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@.com",
            "user..name@domain.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                validate_email_address(email)

    def test_validate_url_valid(self):
        """Test valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://localhost:8080",
            "https://sub.domain.co.uk/path?param=value",
        ]

        for url in valid_urls:
            result = validate_url(url)
            assert result == url

    def test_validate_url_invalid(self):
        """Test invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Unsupported scheme
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
        ]

        for url in invalid_urls:
            with pytest.raises(ValidationError):
                validate_url(url)

    def test_validate_timezone_valid(self):
        """Test valid timezone strings."""
        valid_timezones = ["UTC", "America/New_York", "Europe/London"]
        for tz in valid_timezones:
            result = validate_timezone(tz)
            assert result == tz

    def test_validate_timezone_invalid(self):
        """Test invalid timezone strings."""
        invalid_timezones = ["Invalid/Timezone", "NotATimezone", ""]
        for tz in invalid_timezones:
            with pytest.raises(ValidationError):
                validate_timezone(tz)

    def test_validate_time_format_valid(self):
        """Test valid time format."""
        valid_times = ["09:30", "23:59", "00:00"]
        for time_str in valid_times:
            result = validate_time_format(time_str)
            assert result == time_str

    def test_validate_time_format_invalid(self):
        """Test invalid time format."""
        invalid_times = ["25:00", "12:60", "9:30", "invalid"]
        for time_str in invalid_times:
            with pytest.raises(ValidationError):
                validate_time_format(time_str)

    def test_check_sql_injection_patterns_safe(self):
        """Test SQL injection pattern detection with safe input."""
        safe_inputs = ["normal text", "user input", "hello world"]
        for text in safe_inputs:
            result = check_sql_injection_patterns(text)
            assert result == text

    def test_check_sql_injection_patterns_dangerous(self):
        """Test SQL injection pattern detection with dangerous input."""
        dangerous_inputs = [
            "'; DROP TABLE users; --",
            "UNION SELECT * FROM users",
            "admin' OR '1'='1",
        ]
        for text in dangerous_inputs:
            with pytest.raises(ValidationError):
                check_sql_injection_patterns(text)

    def test_validate_enum_value_valid(self):
        """Test valid enum values."""
        valid_values = ["option1", "option2", "option3"]
        result = validate_enum_value("option1", valid_values)
        assert result == "option1"

    def test_validate_enum_value_invalid(self):
        """Test invalid enum values."""
        valid_values = ["option1", "option2", "option3"]
        with pytest.raises(ValidationError):
            validate_enum_value("invalid_option", valid_values)

    def test_validate_file_path_safe(self):
        """Test safe file paths."""
        safe_paths = ["file.txt", "folder/file.txt", "path/to/file"]
        for path in safe_paths:
            result = validate_file_path(path)
            assert result == path

    def test_validate_file_path_dangerous(self):
        """Test dangerous file paths."""
        dangerous_paths = [
            "../../../etc/passwd",
            "/absolute/path",
            "path\\with\\backslashes",
        ]
        for path in dangerous_paths:
            with pytest.raises(ValidationError):
                validate_file_path(path)

    def test_validate_pagination_params_valid(self):
        """Test valid pagination parameters."""
        result = validate_pagination_params(1, 10)
        assert result == (1, 10)

    def test_validate_pagination_params_invalid(self):
        """Test invalid pagination parameters."""
        with pytest.raises(ValidationError):
            validate_pagination_params(0, 10)  # Page < 1

        with pytest.raises(ValidationError):
            validate_pagination_params(1, 0)  # Page size < 1

        with pytest.raises(ValidationError):
            validate_pagination_params(1, 101)  # Page size > 100

    def test_validate_phone_number_valid(self):
        """Test valid phone numbers."""
        valid_phones = ["+1-555-123-4567", "(555) 123-4567", "5551234567"]
        for phone in valid_phones:
            result = validate_phone_number(phone)
            assert result == phone.strip()

    def test_validate_phone_number_invalid(self):
        """Test invalid phone numbers."""
        invalid_phones = ["123", "1234567890123456", "not-a-phone"]
        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                validate_phone_number(phone)

    def test_validate_json_safe_string_valid(self):
        """Test JSON-safe strings."""
        safe_strings = ["normal text", 'text with "quotes"', "text with \n newlines"]
        for text in safe_strings:
            result = validate_json_safe_string(text)
            assert result == text.strip()

    def test_validate_json_safe_string_invalid(self):
        """Test JSON-unsafe strings."""
        # Control characters that could break JSON
        unsafe_strings = ["text\x00with\x01control", "text\x1fwith\x7fcontrol"]
        for text in unsafe_strings:
            with pytest.raises(ValidationError):
                validate_json_safe_string(text)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_and_none_values(self):
        """Test handling of empty and None values."""
        assert sanitize_text_input(None) is None
        assert sanitize_text_input("") is None
        assert sanitize_text_input("   ") is None

    def test_unicode_handling(self):
        """Test Unicode character handling."""
        unicode_text = "Hello 世界 🌍"
        result = sanitize_text_input(unicode_text)
        assert result == unicode_text

    def test_very_long_inputs(self):
        """Test very long input handling."""
        long_text = "a" * 10000
        with pytest.raises(ValidationError):
            sanitize_text_input(long_text, max_length=1000)

    def test_nested_malicious_patterns(self):
        """Test nested malicious patterns."""
        nested_script = "Hello<script>alert('xss')</script>World"
        with pytest.raises(ValidationError, match="Text contains HTML tags or scripts"):
            sanitize_text_input(nested_script)

    def test_url_edge_cases(self):
        """Test URL validation edge cases."""
        edge_case_urls = [
            "https://example.com:65536",  # Invalid port
            "https://" + "a" * 2000,  # Very long URL
            "https://example.com/../../../etc/passwd",  # Path traversal
        ]

        for url in edge_case_urls:
            with pytest.raises(ValidationError):
                validate_url(url)

    def test_email_edge_cases(self):
        """Test email validation edge cases."""
        edge_case_emails = [
            "a" * 65 + "@domain.com",  # Local part too long
            "user@" + "a" * 254 + ".com",  # Domain too long
            "user@domain..com",  # Double dots
            ".user@domain.com",  # Leading dot
            "user.@domain.com",  # Trailing dot
        ]

        for email in edge_case_emails:
            with pytest.raises(ValidationError):
                validate_email_address(email)


class TestPerformance:
    """Test performance characteristics of validation."""

    def test_large_input_performance(self):
        """Test validation performance with large inputs."""
        # This test ensures validation doesn't hang on large inputs
        large_text = "safe text " * 1000

        # Should complete quickly without hanging
        result = sanitize_text_input(large_text, max_length=20000)
        assert len(result) <= 20000

    def test_many_validations_performance(self):
        """Test performance with many validation calls."""
        # Test that validation scales reasonably
        emails = [f"user{i}@example.com" for i in range(100)]

        for email in emails:
            result = validate_email_address(email)
            assert "@example.com" in result
