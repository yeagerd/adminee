"""
Comprehensive validation utilities for user management service.

Provides custom validators, sanitization functions, and security-focused
input validation for all user-provided data.
"""

import html
import re
from typing import Any, List, Optional, Set
from urllib.parse import urlparse

import pytz

from services.user.utils.email_collision import get_email_collision_detector

# Security patterns for input sanitization
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
DANGEROUS_CHARS_PATTERN = re.compile(r'[<>"\';\\]')
SQL_INJECTION_PATTERNS = [
    re.compile(
        r"(?i)(union|select|insert|update|delete|drop|create|alter)\s", re.IGNORECASE
    ),
    re.compile(r"(?i)(-{2}|/\*|\*/|;)", re.IGNORECASE),
    re.compile(r"(?i)(exec|execute|sp_|xp_)", re.IGNORECASE),
    re.compile(r"'\s*(or|and)\s*'.*?=.*?'", re.IGNORECASE),  # ' OR '=' patterns
    re.compile(r"'\s*(or|and)\s*\d+\s*=\s*\d+", re.IGNORECASE),  # ' OR 1=1 patterns
]

# URL validation patterns
SAFE_URL_PATTERN = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

# Email validation pattern (more strict than basic regex)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Timezone validation
VALID_TIMEZONES: Set[str] = set(pytz.all_timezones)

# Common malicious patterns
MALICIOUS_PATTERNS = [
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"data:", re.IGNORECASE),
    re.compile(r"vbscript:", re.IGNORECASE),
    re.compile(r"onload=", re.IGNORECASE),
    re.compile(r"onerror=", re.IGNORECASE),
    re.compile(r"onclick=", re.IGNORECASE),
]


class ValidationError(ValueError):
    """Custom validation error with field context."""

    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation error for {field}: {reason}")


def sanitize_text_input(
    text: Optional[str], max_length: Optional[int] = None
) -> Optional[str]:
    """
    Sanitize text input to prevent XSS and injection attacks.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text

    Raises:
        ValidationError: If text contains malicious content or exceeds length
    """
    if text is None:
        return None

    # Convert to string if needed
    text = str(text).strip()

    # Check for HTML tags and scripts
    if HTML_TAG_PATTERN.search(text) or SCRIPT_PATTERN.search(text):
        raise ValidationError("text", text, "Text contains HTML tags or scripts")

    # Check for dangerous characters
    if DANGEROUS_CHARS_PATTERN.search(text):
        raise ValidationError("text", text, "Text contains dangerous characters")

    # Check for malicious patterns
    for pattern in MALICIOUS_PATTERNS:
        if pattern.search(text):
            raise ValidationError("text", text, "Text contains malicious content")

    # Check length
    if max_length and len(text) > max_length:
        raise ValidationError(
            "text", text, f"Text exceeds maximum length of {max_length} characters"
        )

    # HTML escape to prevent XSS
    text = html.escape(text)

    return text if text else None


def validate_email_address(email: str) -> str:
    """
    Validate email address format and security.

    Args:
        email: Email address to validate

    Returns:
        Normalized email address

    Raises:
        ValidationError: If email is invalid
    """
    if not email or not email.strip():
        raise ValidationError("email", email, "Email address cannot be empty")

    email = email.strip().lower()

    # Check basic format
    if not EMAIL_PATTERN.match(email):
        raise ValidationError("email", email, "Invalid email format")

    # Check for dangerous patterns
    for pattern in MALICIOUS_PATTERNS:
        if pattern.search(email):
            raise ValidationError("email", email, "Email contains malicious content")

    # Additional security checks
    if len(email) > 254:  # RFC 5321 limit
        raise ValidationError("email", email, "Email address too long")

    local, domain = email.split("@", 1)

    if len(local) > 64:  # RFC 5321 limit for local part
        raise ValidationError("email", email, "Email local part too long")

    if len(domain) > 253:  # RFC 5321 limit for domain
        raise ValidationError("email", email, "Email domain too long")

    # Check for suspicious patterns
    if ".." in email or email.startswith(".") or email.endswith("."):
        raise ValidationError("email", email, "Invalid email format")

    # Check for leading/trailing dots in local part
    if local.startswith(".") or local.endswith("."):
        raise ValidationError("email", email, "Invalid email format")

    return email


async def validate_email_with_collision_check(email: str) -> str:
    """
    Validate email address and check for collisions using normalized email.

    Args:
        email: Email address to validate

    Returns:
        Normalized email address

    Raises:
        ValidationError: If email is invalid or collision detected
    """
    # First validate the email format
    validated_email = validate_email_address(email)

    # Then normalize using email-normalize library
    try:
        normalized_email = await get_email_collision_detector().normalize_email_async(
            validated_email
        )
        return normalized_email
    except Exception:
        # If normalization fails, fall back to basic validation
        return validated_email


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
    """
    Validate URL format and security.

    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (defaults to http/https)

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid or unsafe
    """
    if not url or not url.strip():
        raise ValidationError("url", url, "URL cannot be empty")

    # Check for suspicious patterns first (before stripping)
    suspicious_patterns = ["%00", "%0a", "%0d", "\x00", "\n", "\r"]
    for suspicious_pattern in suspicious_patterns:
        if suspicious_pattern in url.lower():
            raise ValidationError("url", url, "URL contains suspicious characters")

    url = url.strip()

    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    # Additional security checks
    if len(url) > 2048:  # Reasonable URL length limit
        raise ValidationError("url", url, "URL too long")

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError("url", url, "Invalid URL format")

    # Check scheme
    if parsed.scheme.lower() not in allowed_schemes:
        raise ValidationError(
            "url", url, f"URL scheme must be one of: {', '.join(allowed_schemes)}"
        )

    # Check port range (urlparse raises ValueError for invalid ports)
    try:
        port = parsed.port
        if port is not None and (port < 1 or port > 65535):
            raise ValidationError("url", url, "URL port must be between 1 and 65535")
    except ValueError:
        raise ValidationError("url", url, "URL port must be between 1 and 65535")

    # Check for path traversal
    if "../" in parsed.path or "..\\" in parsed.path:
        raise ValidationError("url", url, "URL contains path traversal patterns")

    # Check for malicious patterns
    for pattern in MALICIOUS_PATTERNS:
        if pattern.search(url):
            raise ValidationError("url", url, "URL contains malicious content")

    # Check basic format with regex
    if not SAFE_URL_PATTERN.match(url):
        raise ValidationError("url", url, "Invalid URL format")

    return url


def validate_timezone(timezone_str: str) -> str:
    """
    Validate timezone string.

    Args:
        timezone_str: Timezone string to validate

    Returns:
        Validated timezone string

    Raises:
        ValidationError: If timezone is invalid
    """
    if not timezone_str or not timezone_str.strip():
        raise ValidationError("timezone", timezone_str, "Timezone cannot be empty")

    timezone_str = timezone_str.strip()

    # Check if it's a valid pytz timezone
    if timezone_str not in VALID_TIMEZONES:
        raise ValidationError("timezone", timezone_str, "Invalid timezone")

    return timezone_str


def validate_time_format(time_str: str) -> str:
    """
    Validate time format (HH:MM).

    Args:
        time_str: Time string to validate

    Returns:
        Validated time string

    Raises:
        ValidationError: If time format is invalid
    """
    if not time_str or not time_str.strip():
        raise ValidationError("time", time_str, "Time cannot be empty")

    time_str = time_str.strip()

    # Check format
    if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", time_str):
        raise ValidationError(
            "time", time_str, "Time must be in HH:MM format (24-hour)"
        )

    return time_str


def validate_phone_number(phone: str) -> str:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Normalized phone number

    Raises:
        ValidationError: If phone number is invalid
    """
    if not phone or not phone.strip():
        raise ValidationError("phone", phone, "Phone number cannot be empty")

    # Remove all non-digit characters for validation
    digits_only = re.sub(r"[^\d]", "", phone)

    # Check length (international format)
    if len(digits_only) < 10 or len(digits_only) > 15:
        raise ValidationError("phone", phone, "Phone number must be 10-15 digits")

    # Check for dangerous patterns
    for pattern in MALICIOUS_PATTERNS:
        if pattern.search(phone):
            raise ValidationError(
                "phone", phone, "Phone number contains malicious content"
            )

    return phone.strip()


def validate_json_safe_string(text: str, field_name: str = "text") -> str:
    """
    Validate that string is safe for JSON serialization.

    Args:
        text: Text to validate
        field_name: Name of the field for error messages

    Returns:
        Validated text

    Raises:
        ValidationError: If text contains unsafe characters
    """
    if not text or not text.strip():
        raise ValidationError(field_name, text, f"{field_name} cannot be empty")

    text = text.strip()

    # Check for control characters that could break JSON
    control_chars = [
        chr(i) for i in range(32) if i not in [9, 10, 13]
    ]  # Allow tab, LF, CR
    for char in control_chars:
        if char in text:
            raise ValidationError(
                field_name, text, f"{field_name} contains unsafe control characters"
            )

    # Check for unpaired surrogate characters
    try:
        text.encode("utf-8").decode("utf-8")
    except UnicodeError:
        raise ValidationError(
            field_name, text, f"{field_name} contains invalid Unicode characters"
        )

    return text


def check_sql_injection_patterns(text: str, field_name: str = "text") -> str:
    """
    Check for SQL injection patterns in text.

    Args:
        text: Text to check
        field_name: Name of the field for error messages

    Returns:
        Original text if safe

    Raises:
        ValidationError: If SQL injection patterns detected
    """
    if not text:
        return text

    text_str = str(text)

    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text_str):
            raise ValidationError(
                field_name, text, f"{field_name} contains SQL injection patterns"
            )

    return text_str


def validate_enum_value(
    value: str, valid_values: List[str], field_name: str = "value"
) -> str:
    """
    Validate that value is in the list of valid values.

    Args:
        value: Value to validate
        valid_values: List of valid values
        field_name: Name of the field for error messages

    Returns:
        Validated value

    Raises:
        ValidationError: If value is not in valid_values
    """
    if not value or not value.strip():
        raise ValidationError(field_name, value, f"{field_name} cannot be empty")

    value = value.strip()

    if value not in valid_values:
        raise ValidationError(
            field_name,
            value,
            f"{field_name} must be one of: {', '.join(valid_values)}",
        )

    return value


def validate_file_path(file_path: str) -> str:
    """
    Validate file path for security.

    Args:
        file_path: File path to validate

    Returns:
        Validated file path

    Raises:
        ValidationError: If file path is unsafe
    """
    if not file_path or not file_path.strip():
        raise ValidationError("file_path", file_path, "File path cannot be empty")

    file_path = file_path.strip()

    # Check for path traversal
    if ".." in file_path or "\\" in file_path:
        raise ValidationError(
            "file_path", file_path, "File path contains unsafe patterns"
        )

    # Check for absolute paths
    if file_path.startswith("/") or file_path.startswith("\\"):
        raise ValidationError("file_path", file_path, "File path cannot be absolute")

    # Check for dangerous patterns
    for pattern in MALICIOUS_PATTERNS:
        if pattern.search(file_path):
            raise ValidationError(
                "file_path", file_path, "File path contains malicious content"
            )

    return file_path


def validate_pagination_params(page: int, page_size: int) -> tuple[int, int]:
    """
    Validate pagination parameters.

    Args:
        page: Page number
        page_size: Number of items per page

    Returns:
        Tuple of (page, page_size)

    Raises:
        ValidationError: If parameters are invalid
    """
    if page < 1:
        raise ValidationError("page", page, "Page number must be at least 1")

    if page_size < 1:
        raise ValidationError("page_size", page_size, "Page size must be at least 1")

    if page_size > 100:
        raise ValidationError("page_size", page_size, "Page size cannot exceed 100")

    return page, page_size


# Pydantic validators


def text_validator(max_length: Optional[int] = None):
    """Create a Pydantic validator for text fields."""

    def validator(cls, v):
        if v is None:
            return v
        return sanitize_text_input(v, max_length)

    return validator


def email_validator():
    """Create a Pydantic validator for email fields."""

    def validator(cls, v):
        if v is None:
            return v
        return validate_email_address(v)

    return validator


async def email_validator_with_collision_check():
    """Create a Pydantic validator for email fields with collision checking."""

    async def validator(cls, v):
        if v is None:
            return v
        return await validate_email_with_collision_check(v)

    return validator


def url_validator(allowed_schemes: Optional[List[str]] = None):
    """Create a Pydantic validator for URL fields."""

    def validator(cls, v):
        if v is None:
            return v
        return validate_url(v, allowed_schemes)

    return validator


def timezone_validator():
    """Create a Pydantic validator for timezone fields."""

    def validator(cls, v):
        if v is None:
            return v
        return validate_timezone(v)

    return validator


def time_validator():
    """Create a Pydantic validator for time fields."""

    def validator(cls, v):
        if v is None:
            return v
        return validate_time_format(v)

    return validator
