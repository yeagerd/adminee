import hashlib
import os
import secrets
import string
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class TokenGenerator:
    """Utility class for generating secure tokens for booking links"""

    @staticmethod
    def generate_evergreen_token() -> str:
        """Generate a secure token for evergreen booking links"""
        # Generate a 16-character alphanumeric token
        alphabet = string.ascii_letters + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(16))
        return f"bl_{token}"

    @staticmethod
    def generate_one_time_token() -> str:
        """Generate a secure token for one-time booking links"""
        # Generate a 20-character alphanumeric token for one-time links
        alphabet = string.ascii_letters + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(20))
        return f"ot_{token}"

    @staticmethod
    def generate_slug() -> str:
        """Generate a URL-friendly slug for booking links"""
        # Generate a 32-character lowercase alphanumeric slug for security
        # This provides 2^160 possible combinations, making brute force attacks impractical
        alphabet = string.ascii_lowercase + string.digits
        slug = "".join(secrets.choice(alphabet) for _ in range(32))
        return slug


class RateLimiter:
    """Simple in-memory rate limiter for API endpoints"""

    def __init__(self) -> None:
        self.requests: Dict[str, List[float]] = (
            {}
        )  # In production, use Redis or similar

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if a request is allowed based on rate limiting rules

        Args:
            key: Unique identifier for the client (IP, user ID, etc.)
            max_requests: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        window_start = now - window_seconds

        # Clean old entries
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key] if req_time > window_start
            ]
        else:
            self.requests[key] = []

        # Check if under limit
        if len(self.requests[key]) < max_requests:
            self.requests[key].append(now)
            return True

        return False

    def get_remaining_requests(
        self, key: str, max_requests: int, window_seconds: int
    ) -> int:
        """Get the number of remaining requests for a client"""
        now = time.time()
        window_start = now - window_seconds

        if key in self.requests:
            recent_requests = [
                req_time for req_time in self.requests[key] if req_time > window_start
            ]
            return max(0, max_requests - len(recent_requests))

        return max_requests


class SecurityUtils:
    """General security utilities for the booking system"""

    @staticmethod
    def hash_email(email: str) -> str:
        """Hash an email address for privacy in analytics"""
        return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

    @staticmethod
    def validate_token_format(token: str) -> bool:
        """Validate that a token has the correct format"""
        if not token:
            return False

        # Check if it's a valid booking link or one-time token
        if token.startswith("bl_") and len(token) == 19:  # bl_ + 16 chars
            return True
        elif token.startswith("ot_") and len(token) == 23:  # ot_ + 20 chars
            return True

        return False

    @staticmethod
    def validate_public_token_format(token: str) -> bool:
        """Validate that a public endpoint token is valid (accepts both one-time tokens and evergreen slugs)"""
        if not token:
            return False

        # Check if it's a valid one-time token (ot_ prefix)
        if token.startswith("ot_") and len(token) == 23:  # ot_ + 20 chars
            return True

        # Check if it's a valid evergreen slug (any non-empty string up to 64 chars)
        if len(token) <= 64 and not token.startswith(("bl_", "ot_")):
            return True

        return False

    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """Sanitize user input to prevent injection attacks"""
        if not text:
            return ""

        # Remove potentially dangerous characters
        sanitized = text.replace("<", "&lt;").replace(">", "&gt;")
        sanitized = sanitized.replace('"', "&quot;").replace("'", "&#x27;")

        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()


# Global rate limiter instance
rate_limiter = RateLimiter()

# Test mode flag - can be set by tests to control rate limiting behavior
_test_mode = False


def set_test_mode(enabled: bool) -> None:
    """Enable or disable test mode for rate limiting"""
    global _test_mode
    _test_mode = enabled


def check_rate_limit(
    client_key: str, max_requests: int = 100, window_seconds: int = 3600
) -> bool:
    """
    Check if a client is within rate limits

    Args:
        client_key: Unique identifier for the client
        max_requests: Maximum requests per window (default: 100 per hour)
        window_seconds: Time window in seconds (default: 1 hour)

    Returns:
        True if within limits, False if rate limited
    """
    # Disable rate limiting in test mode
    if _test_mode:
        return True

    return rate_limiter.is_allowed(client_key, max_requests, window_seconds)


def get_remaining_requests(
    client_key: str, max_requests: int = 100, window_seconds: int = 3600
) -> int:
    """Get remaining requests for a client"""
    return rate_limiter.get_remaining_requests(client_key, max_requests, window_seconds)
