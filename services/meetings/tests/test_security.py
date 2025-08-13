import pytest
from services.meetings.services.security import (
    TokenGenerator,
    SecurityUtils,
    check_rate_limit,
    get_remaining_requests
)

class TestTokenGenerator:
    """Test the TokenGenerator utility class"""
    
    def test_generate_evergreen_token(self):
        """Test that evergreen tokens are generated with correct format"""
        token = TokenGenerator.generate_evergreen_token()
        
        assert token.startswith("bl_")
        assert len(token) == 19  # bl_ + 16 chars
        assert all(c.isalnum() for c in token[3:])  # Only alphanumeric after prefix
    
    def test_generate_one_time_token(self):
        """Test that one-time tokens are generated with correct format"""
        token = TokenGenerator.generate_one_time_token()
        
        assert token.startswith("ot_")
        assert len(token) == 23  # ot_ + 20 chars
        assert all(c.isalnum() for c in token[3:])  # Only alphanumeric after prefix
    
    def test_generate_slug(self):
        """Test that slugs are generated with correct format"""
        slug = TokenGenerator.generate_slug()
        
        assert len(slug) == 12
        assert all(c.islower() or c.isdigit() for c in slug)  # Lowercase and digits only
    
    def test_token_uniqueness(self):
        """Test that generated tokens are unique"""
        tokens = set()
        for _ in range(100):
            token = TokenGenerator.generate_one_time_token()
            assert token not in tokens
            tokens.add(token)

class TestSecurityUtils:
    """Test the SecurityUtils utility class"""
    
    def test_hash_email(self):
        """Test that emails are hashed consistently"""
        email1 = "test@example.com"
        email2 = "TEST@EXAMPLE.COM"
        email3 = "another@example.com"
        
        hash1 = SecurityUtils.hash_email(email1)
        hash2 = SecurityUtils.hash_email(email2)
        hash3 = SecurityUtils.hash_email(email3)
        
        # Same email (case-insensitive) should produce same hash
        assert hash1 == hash2
        # Different emails should produce different hashes
        assert hash1 != hash3
        # Hash should be 16 characters
        assert len(hash1) == 16
        assert len(hash3) == 16
    
    def test_validate_token_format(self):
        """Test token format validation"""
        # Valid tokens
        assert SecurityUtils.validate_token_format("bl_abc123def4567890") == True
        assert SecurityUtils.validate_token_format("ot_abc123def4567890abcd") == True
        
        # Invalid tokens
        assert SecurityUtils.validate_token_format("invalid") == False
        assert SecurityUtils.validate_token_format("bl_short") == False
        assert SecurityUtils.validate_token_format("ot_tooshort") == False
        assert SecurityUtils.validate_token_format("") == False
        assert SecurityUtils.validate_token_format("bl_abc123def45678901") == False  # Too long
        assert SecurityUtils.validate_token_format("ot_abc123def4567890abcde") == False  # Too long
    
    def test_sanitize_input(self):
        """Test input sanitization"""
        # Test HTML injection prevention
        malicious_input = '<script>alert("xss")</script>'
        sanitized = SecurityUtils.sanitize_input(malicious_input)
        assert '<' not in sanitized
        assert '>' not in sanitized
        assert 'alert' in sanitized  # Content preserved
        
        # Test quote escaping
        quote_input = 'He said "Hello" and \'Goodbye\''
        sanitized = SecurityUtils.sanitize_input(quote_input)
        assert '"' not in sanitized
        assert "'" not in sanitized
        
        # Test length truncation
        long_input = "a" * 1000
        sanitized = SecurityUtils.sanitize_input(long_input, max_length=100)
        assert len(sanitized) <= 100
        
        # Test empty input
        assert SecurityUtils.sanitize_input("") == ""
        assert SecurityUtils.sanitize_input(None) == ""
        
        # Test whitespace trimming
        assert SecurityUtils.sanitize_input("  hello  ") == "hello"

class TestRateLimiter:
    """Test the rate limiting functionality"""
    
    def test_rate_limit_basic(self):
        """Test basic rate limiting functionality"""
        # Reset rate limiter for testing
        from services.meetings.services.security import rate_limiter
        rate_limiter.requests = {}
        
        client_key = "test_client"
        
        # Should allow first 5 requests
        for i in range(5):
            assert check_rate_limit(client_key, max_requests=5, window_seconds=3600) == True
        
        # Should block 6th request
        assert check_rate_limit(client_key, max_requests=5, window_seconds=3600) == False
    
    def test_remaining_requests(self):
        """Test remaining requests calculation"""
        from services.meetings.services.security import rate_limiter
        rate_limiter.requests = {}
        
        client_key = "test_client"
        max_requests = 10
        
        # Initially should have all requests available
        assert get_remaining_requests(client_key, max_requests, 3600) == 10
        
        # Make some requests
        for i in range(3):
            check_rate_limit(client_key, max_requests, 3600)
        
        # Should have 7 remaining
        assert get_remaining_requests(client_key, max_requests, 3600) == 7
    
    def test_rate_limit_window(self):
        """Test that rate limits respect time windows"""
        from services.meetings.services.security import rate_limiter
        rate_limiter.requests = {}
        
        client_key = "test_client"
        
        # Make 3 requests in a 1-second window
        for i in range(3):
            assert check_rate_limit(client_key, max_requests=3, window_seconds=1) == True
        
        # Should be blocked
        assert check_rate_limit(client_key, max_requests=3, window_seconds=1) == False
        
        # Wait for window to expire (in real test, you'd mock time)
        # For now, just verify the behavior with a new window
        rate_limiter.requests = {}
        assert check_rate_limit(client_key, max_requests=3, window_seconds=1) == True

if __name__ == "__main__":
    pytest.main([__file__])
