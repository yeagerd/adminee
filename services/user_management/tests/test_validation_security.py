"""
Unit tests for validation utilities and security features.

Tests comprehensive validation, sanitization, and security measures
including edge cases and malicious input attempts.
"""

import pytest
from pydantic import ValidationError as PydanticValidationError

from ..middleware.sanitization import (
    is_safe_text,
    sanitize_user_input,
)
from ..schemas.integration import OAuthCallbackRequest, OAuthStartRequest
from ..schemas.preferences import (
    AIPreferencesSchema,
    NotificationPreferencesSchema,
    PreferencesImportRequest,
)
from ..schemas.user import UserCreate, UserSearchRequest, UserUpdate
from ..utils.validation import ValidationError as CustomValidationError
from ..utils.validation import (
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
        result = sanitize_text_input("<script>alert('xss')</script>Hello")
        assert result == "Hello"
        assert "<script>" not in result

    def test_sanitize_text_input_dangerous_chars(self):
        """Test dangerous character removal."""
        result = sanitize_text_input('Hello"World<test>')
        assert '"' not in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_text_input_max_length(self):
        """Test maximum length enforcement."""
        long_text = "a" * 200
        with pytest.raises(CustomValidationError) as exc_info:
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
            with pytest.raises(CustomValidationError):
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
            "user..double@domain.com",
            "user@domain",
            "a" * 250 + "@domain.com",  # Too long
        ]

        for email in invalid_emails:
            with pytest.raises(CustomValidationError):
                validate_email_address(email)

    def test_validate_email_address_malicious(self):
        """Test malicious email patterns."""
        malicious_emails = [
            "user@domain.com<script>alert('xss')</script>",
            "javascript:alert('xss')@domain.com",
            "user@domain.com'OR'1'='1",
        ]

        for email in malicious_emails:
            with pytest.raises(CustomValidationError):
                validate_email_address(email)

    def test_validate_url_valid(self):
        """Test valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://localhost:8000",
            "https://sub.domain.co.uk/path?param=value",
            "https://192.168.1.1:3000",
        ]

        for url in valid_urls:
            result = validate_url(url)
            assert result == url

    def test_validate_url_invalid(self):
        """Test invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Wrong scheme
            "https://",
            "http://",
            "javascript:alert('xss')",
            "data:text/html,<script>",
        ]

        for url in invalid_urls:
            with pytest.raises(CustomValidationError):
                validate_url(url)

    def test_validate_url_suspicious_patterns(self):
        """Test URLs with suspicious patterns."""
        suspicious_urls = [
            "https://example.com%00",
            "https://example.com%0a",
            "https://example.com\x00",
            "https://example.com\n",
        ]

        for url in suspicious_urls:
            with pytest.raises(CustomValidationError):
                validate_url(url, allowed_schemes=["https"])

    def test_validate_timezone_valid(self):
        """Test valid timezones."""
        valid_timezones = [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
        ]

        for tz in valid_timezones:
            result = validate_timezone(tz)
            assert result == tz

    def test_validate_timezone_invalid(self):
        """Test invalid timezones."""
        invalid_timezones = [
            "Invalid/Timezone",
            "UTC+5",  # Not a pytz timezone
            "BadTimezone",  # Invalid
            "",
        ]

        for tz in invalid_timezones:
            with pytest.raises(CustomValidationError):
                validate_timezone(tz)

    def test_validate_time_format_valid(self):
        """Test valid time formats."""
        valid_times = [
            "00:00",
            "12:30",
            "23:59",
            "09:15",
        ]

        for time_str in valid_times:
            result = validate_time_format(time_str)
            assert result == time_str

    def test_validate_time_format_invalid(self):
        """Test invalid time formats."""
        invalid_times = [
            "24:00",  # Invalid hour
            "12:60",  # Invalid minute
            "12:30:45",  # Seconds not allowed
            "12",  # Missing minutes
            "12:3",  # Single digit minute
            "ab:cd",  # Non-numeric
        ]

        for time_str in invalid_times:
            with pytest.raises(CustomValidationError):
                validate_time_format(time_str)

    def test_validate_phone_number_valid(self):
        """Test valid phone numbers."""
        valid_phones = [
            "+1-555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "15551234567",
            "+44 20 7946 0958",
        ]

        for phone in valid_phones:
            result = validate_phone_number(phone)
            assert result == phone.strip()

    def test_validate_phone_number_invalid(self):
        """Test invalid phone numbers."""
        invalid_phones = [
            "123",  # Too short
            "1" * 20,  # Too long
            "abc-def-ghij",  # Non-numeric
            "",
        ]

        for phone in invalid_phones:
            with pytest.raises(CustomValidationError):
                validate_phone_number(phone)

    def test_check_sql_injection_patterns(self):
        """Test SQL injection pattern detection."""
        safe_texts = [
            "Hello World",
            "user@example.com",
            "Normal text with numbers 123",
        ]

        for text in safe_texts:
            result = check_sql_injection_patterns(text)
            assert result == text

        malicious_texts = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM passwords",
            "/* comment */ SELECT",
            "exec sp_executesql",
        ]

        for text in malicious_texts:
            with pytest.raises(CustomValidationError):
                check_sql_injection_patterns(text)

    def test_validate_json_safe_string(self):
        """Test JSON-safe string validation."""
        safe_strings = [
            "Hello World",
            "Text with\ttab",
            "Text with\nnewline",
            "Text with\rcarriage return",
        ]

        for text in safe_strings:
            result = validate_json_safe_string(text)
            assert result == text

        unsafe_strings = [
            "Text with\x00null byte",
            "Text with\x01control char",
            "Text with\x1fmore control",
        ]

        for text in unsafe_strings:
            with pytest.raises(CustomValidationError):
                validate_json_safe_string(text)

    def test_validate_enum_value(self):
        """Test enum value validation."""
        valid_values = ["option1", "option2", "option3"]

        # Valid case
        result = validate_enum_value("option1", valid_values)
        assert result == "option1"

        # Invalid case
        with pytest.raises(CustomValidationError):
            validate_enum_value("invalid", valid_values)

    def test_validate_file_path(self):
        """Test file path validation."""
        safe_paths = [
            "documents/file.txt",
            "folder/subfolder/file.pdf",
            "simple_file.doc",
        ]

        for path in safe_paths:
            result = validate_file_path(path)
            assert result == path

        dangerous_paths = [
            "../../../etc/passwd",
            "..\\windows\\system32",
            "/etc/shadow",
            "~/.ssh/id_rsa",
            "file\x00.txt",
        ]

        for path in dangerous_paths:
            with pytest.raises(CustomValidationError):
                validate_file_path(path)

    def test_validate_pagination_params(self):
        """Test pagination parameter validation."""
        # Valid cases
        page, page_size = validate_pagination_params(1, 20)
        assert page == 1
        assert page_size == 20

        page, page_size = validate_pagination_params(100, 50)
        assert page == 100
        assert page_size == 50

        # Invalid cases
        with pytest.raises(CustomValidationError):
            validate_pagination_params(0, 20)  # Page < 1

        with pytest.raises(CustomValidationError):
            validate_pagination_params(1, 0)  # Page size < 1

        with pytest.raises(CustomValidationError):
            validate_pagination_params(10001, 20)  # Page too large

        with pytest.raises(CustomValidationError):
            validate_pagination_params(1, 1001)  # Page size too large


class TestSchemaValidation:
    """Test cases for enhanced schema validation."""

    def test_user_create_valid(self):
        """Test valid user creation."""
        user_data = {
            "external_auth_id": "user_abc123",
            "auth_provider": "clerk",
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "profile_image_url": "https://example.com/image.jpg",
        }

        user = UserCreate(**user_data)
        assert user.external_auth_id == "user_abc123"
        assert user.auth_provider == "clerk"
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_user_create_malicious_input(self):
        """Test user creation with malicious input."""
        malicious_data = {
            "external_auth_id": "user_abc123",
            "auth_provider": "clerk",
            "email": "test@example.com",
            "first_name": "<script>alert('xss')</script>John",
            "last_name": "Doe'; DROP TABLE users; --",
            "profile_image_url": "javascript:alert('xss')",
        }

        with pytest.raises(PydanticValidationError):
            UserCreate(**malicious_data)

    def test_user_update_sanitization(self):
        """Test user update with input sanitization."""
        update_data = {
            "first_name": "  John  ",  # Whitespace
            "last_name": "Doe<script>",  # HTML
            "profile_image_url": "https://example.com/image.jpg",
        }

        user = UserUpdate(**update_data)
        assert user.first_name == "John"  # Trimmed
        assert "<script>" not in user.last_name  # HTML removed

    def test_user_search_query_sanitization(self):
        """Test search query sanitization."""
        search_data = {
            "query": "John'; DROP TABLE users; --",
            "page": 1,
            "page_size": 20,
        }

        with pytest.raises(PydanticValidationError):
            UserSearchRequest(**search_data)

    def test_notification_preferences_time_validation(self):
        """Test notification preferences time validation."""
        # Valid case
        prefs_data = {
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
        }

        prefs = NotificationPreferencesSchema(**prefs_data)
        assert prefs.quiet_hours_start == "22:00"
        assert prefs.quiet_hours_end == "08:00"

        # Invalid case
        invalid_data = {
            "quiet_hours_start": "25:00",  # Invalid hour
            "quiet_hours_end": "08:60",  # Invalid minute
        }

        with pytest.raises(PydanticValidationError):
            NotificationPreferencesSchema(**invalid_data)

    def test_ai_preferences_enum_validation(self):
        """Test AI preferences enum validation."""
        # Valid case
        ai_data = {
            "response_style": "balanced",
            "response_length": "medium",
        }

        ai_prefs = AIPreferencesSchema(**ai_data)
        assert ai_prefs.response_style == "balanced"
        assert ai_prefs.response_length == "medium"

        # Invalid case
        invalid_data = {
            "response_style": "invalid_style",
            "response_length": "invalid_length",
        }

        with pytest.raises(PydanticValidationError):
            AIPreferencesSchema(**invalid_data)

    def test_oauth_start_request_validation(self):
        """Test OAuth start request validation."""
        # Valid case
        oauth_data = {
            "provider": "google",
            "redirect_uri": "https://app.example.com/callback",
            "scopes": ["read", "write"],
        }

        oauth_req = OAuthStartRequest(**oauth_data)
        assert oauth_req.redirect_uri == "https://app.example.com/callback"
        assert set(oauth_req.scopes) == {
            "read",
            "write",
        }  # Use set comparison for order independence

        # Invalid case - malicious redirect URI
        invalid_data = {
            "provider": "google",
            "redirect_uri": "javascript:alert('xss')",
            "scopes": ["read"],
        }

        with pytest.raises(PydanticValidationError):
            OAuthStartRequest(**invalid_data)

    def test_oauth_callback_validation(self):
        """Test OAuth callback validation."""
        # Valid case
        callback_data = {
            "code": "auth_code_123",
            "state": "state_token_456",
        }

        callback = OAuthCallbackRequest(**callback_data)
        assert callback.code == "auth_code_123"
        assert callback.state == "state_token_456"

        # Invalid case - malicious state
        invalid_data = {
            "code": "auth_code_123",
            "state": "'; DROP TABLE oauth_states; --",
        }

        with pytest.raises(PydanticValidationError):
            OAuthCallbackRequest(**invalid_data)

    def test_preferences_import_validation(self):
        """Test preferences import validation."""
        # Valid case
        import_data = {
            "preferences": {"ui": {"theme": "dark"}},
            "merge_strategy": "merge",
        }

        import_req = PreferencesImportRequest(**import_data)
        assert import_req.merge_strategy == "merge"

        # Invalid case
        invalid_data = {
            "preferences": {"ui": {"theme": "dark"}},
            "merge_strategy": "invalid_strategy",
        }

        with pytest.raises(PydanticValidationError):
            PreferencesImportRequest(**invalid_data)


class TestSecurityMiddleware:
    """Test cases for security middleware."""

    def test_is_safe_text(self):
        """Test safe text detection."""
        assert is_safe_text("Hello World") is True
        assert is_safe_text("Normal text with numbers 123") is True
        assert is_safe_text("'; DROP TABLE users; --") is False
        assert is_safe_text("Text with\x00null byte") is False

    def test_sanitize_user_input(self):
        """Test user input sanitization."""
        input_data = {
            "name": "John<script>alert('xss')</script>",
            "email": "john@example.com",
            "password": "secret123",  # Should be skipped
            "description": "Normal text",
        }

        sanitized = sanitize_user_input(input_data)

        assert "<script>" not in sanitized["name"]
        assert sanitized["email"] == "john@example.com"
        assert sanitized["password"] == "secret123"  # Unchanged
        assert sanitized["description"] == "Normal text"

    def test_sanitize_user_input_custom_skip_fields(self):
        """Test user input sanitization with custom skip fields."""
        input_data = {
            "name": "John<script>",
            "token": "bearer_token_123",
            "custom_field": "sensitive_data",
        }

        skip_fields = {"token", "custom_field"}
        sanitized = sanitize_user_input(input_data, skip_fields)

        assert "<script>" not in sanitized["name"]
        assert sanitized["token"] == "bearer_token_123"  # Unchanged
        assert sanitized["custom_field"] == "sensitive_data"  # Unchanged


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
        with pytest.raises(CustomValidationError):
            sanitize_text_input(long_text, max_length=1000)

    def test_nested_malicious_patterns(self):
        """Test nested malicious patterns."""
        nested_script = "<scr<script>ipt>alert('xss')</script>"
        result = sanitize_text_input(nested_script)
        assert "script" not in result.lower()
        assert "alert" not in result

    def test_url_edge_cases(self):
        """Test URL validation edge cases."""
        edge_case_urls = [
            "https://example.com:65536",  # Invalid port
            "https://" + "a" * 2000,  # Very long URL
            "https://example.com/../../../etc/passwd",  # Path traversal
        ]

        for url in edge_case_urls:
            with pytest.raises(CustomValidationError):
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
            with pytest.raises(CustomValidationError):
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
