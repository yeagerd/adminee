"""
Unit tests for token encryption functionality.

Tests cover encryption/decryption operations, key derivation,
error handling, and security scenarios.
"""

import base64
import os
from unittest.mock import Mock, patch

import pytest

from services.user_management.exceptions import EncryptionException
from services.user_management.security.encryption import TokenEncryption
from services.user_management.settings import Settings


class TestTokenEncryption:
    """Test cases for TokenEncryption class."""

    @pytest.fixture
    def settings(self):
        """Create test settings with encryption configuration."""
        return Settings(
            token_encryption_salt=base64.b64encode(b"test-salt-16byte").decode("utf-8")
        )

    @pytest.fixture
    def encryption_service(self, settings):
        """Create TokenEncryption service with test settings."""
        return TokenEncryption(settings)

    @pytest.fixture
    def sample_tokens(self):
        """Sample tokens for testing."""
        return {
            "access_token": "ya29.a0AfH6SMC...",
            "refresh_token": "1//0GWJ9QaSlKL...",
            "oauth_token": "EAABwzLixnjYBAO...",
            "api_key": "sk-1234567890abcdef",
        }

    def test_initialization_with_settings(self, settings):
        """Test encryption service initialization with provided settings."""
        service = TokenEncryption(settings)
        assert service.settings == settings
        assert service._service_salt is not None
        assert len(service._service_salt) == 16

    def test_initialization_without_settings(self):
        """Test encryption service initialization with default settings."""
        service = TokenEncryption()
        assert service.settings is not None
        assert service._service_salt is not None
        assert len(service._service_salt) == 16

    def test_service_salt_from_env(self):
        """Test service salt loading from environment variable."""
        test_salt = base64.b64encode(b"custom-salt-16byt").decode("utf-8")
        settings = Settings(token_encryption_salt=test_salt)
        service = TokenEncryption(settings)

        expected_salt = base64.b64decode(test_salt)
        assert service._service_salt == expected_salt

    def test_service_salt_default_fallback(self):
        """Test service salt fallback when not provided."""
        settings = Settings(token_encryption_salt=None)
        service = TokenEncryption(settings)

        # Should generate deterministic salt from service name
        expected_salt = "briefly-user-management".encode("utf-8").ljust(16, b"\x00")[
            :16
        ]
        assert service._service_salt == expected_salt

    def test_derive_user_key_consistency(self, encryption_service):
        """Test that user key derivation is consistent for same inputs."""
        user_id = "user_123"

        key1 = encryption_service.derive_user_key(user_id)
        key2 = encryption_service.derive_user_key(user_id)

        assert key1 == key2
        assert len(key1) == 32  # 256 bits
        assert len(key2) == 32

    def test_derive_user_key_different_users(self, encryption_service):
        """Test that different users get different keys."""
        user1_key = encryption_service.derive_user_key("user_123")
        user2_key = encryption_service.derive_user_key("user_456")

        assert user1_key != user2_key
        assert len(user1_key) == 32
        assert len(user2_key) == 32

    def test_derive_user_key_different_versions(self, encryption_service):
        """Test that different key versions produce different keys."""
        user_id = "user_123"

        key_v1 = encryption_service.derive_user_key(user_id, version=1)
        key_v2 = encryption_service.derive_user_key(user_id, version=2)

        assert key_v1 != key_v2
        assert len(key_v1) == 32
        assert len(key_v2) == 32

    def test_encrypt_decrypt_roundtrip(self, encryption_service, sample_tokens):
        """Test that encryption and decryption work correctly."""
        user_id = "user_123"

        for token_type, token in sample_tokens.items():
            # Encrypt token
            encrypted = encryption_service.encrypt_token(token, user_id)

            # Verify encrypted format
            assert isinstance(encrypted, str)
            assert encrypted != token
            assert len(encrypted) > len(token)

            # Decrypt token
            decrypted = encryption_service.decrypt_token(encrypted, user_id)

            # Verify round-trip
            assert decrypted == token

    def test_encrypt_with_additional_data(self, encryption_service):
        """Test encryption with additional authenticated data."""
        user_id = "user_123"
        token = "test-token"
        additional_data = "provider:google"

        # Encrypt with AAD
        encrypted = encryption_service.encrypt_token(token, user_id, additional_data)

        # Decrypt with correct AAD
        decrypted = encryption_service.decrypt_token(
            encrypted, user_id, additional_data
        )
        assert decrypted == token

        # Decrypt with wrong AAD should fail
        with pytest.raises(EncryptionException):
            encryption_service.decrypt_token(encrypted, user_id, "wrong-aad")

        # Decrypt without AAD should fail
        with pytest.raises(EncryptionException):
            encryption_service.decrypt_token(encrypted, user_id)

    def test_encrypted_tokens_are_different(self, encryption_service):
        """Test that encrypting the same token multiple times produces different ciphertext."""
        user_id = "user_123"
        token = "same-token"

        encrypted1 = encryption_service.encrypt_token(token, user_id)
        encrypted2 = encryption_service.encrypt_token(token, user_id)

        # Should be different due to random nonce
        assert encrypted1 != encrypted2

        # But both should decrypt to same plaintext
        decrypted1 = encryption_service.decrypt_token(encrypted1, user_id)
        decrypted2 = encryption_service.decrypt_token(encrypted2, user_id)
        assert decrypted1 == decrypted2 == token

    def test_user_isolation(self, encryption_service):
        """Test that users cannot decrypt each other's tokens."""
        token = "secret-token"
        user1_id = "user_123"
        user2_id = "user_456"

        # User 1 encrypts token
        encrypted = encryption_service.encrypt_token(token, user1_id)

        # User 1 can decrypt their own token
        decrypted = encryption_service.decrypt_token(encrypted, user1_id)
        assert decrypted == token

        # User 2 cannot decrypt user 1's token
        with pytest.raises(EncryptionException):
            encryption_service.decrypt_token(encrypted, user2_id)

    def test_encrypt_empty_token_fails(self, encryption_service):
        """Test that encrypting empty token raises exception."""
        user_id = "user_123"

        with pytest.raises(EncryptionException) as exc_info:
            encryption_service.encrypt_token("", user_id)

        # Check that it's an encryption exception for the right user
        assert "Failed to encrypt token for user user_123" in str(exc_info.value)

    def test_decrypt_empty_token_fails(self, encryption_service):
        """Test that decrypting empty token raises exception."""
        user_id = "user_123"

        with pytest.raises(EncryptionException) as exc_info:
            encryption_service.decrypt_token("", user_id)

        # Check that it's a decryption exception for the right user
        assert "Failed to decrypt token for user user_123" in str(exc_info.value)

    def test_decrypt_invalid_base64_fails(self, encryption_service):
        """Test that decrypting invalid base64 raises exception."""
        user_id = "user_123"
        invalid_token = "not-valid-base64!!!"

        with pytest.raises(EncryptionException) as exc_info:
            encryption_service.decrypt_token(invalid_token, user_id)

        # Check that it's a decryption exception for the right user
        assert "Failed to decrypt token for user user_123" in str(exc_info.value)

    def test_decrypt_too_short_data_fails(self, encryption_service):
        """Test that decrypting too short data raises exception."""
        user_id = "user_123"
        too_short = base64.b64encode(b"short").decode("utf-8")

        with pytest.raises(EncryptionException) as exc_info:
            encryption_service.decrypt_token(too_short, user_id)

        # Check that it's a decryption exception for the right user
        assert "Failed to decrypt token for user user_123" in str(exc_info.value)

    def test_decrypt_corrupted_data_fails(self, encryption_service):
        """Test that decrypting corrupted data raises exception."""
        user_id = "user_123"
        token = "test-token"

        # Encrypt valid token
        encrypted = encryption_service.encrypt_token(token, user_id)

        # Corrupt the encrypted data
        encrypted_bytes = base64.b64decode(encrypted)
        corrupted_bytes = encrypted_bytes[:-1] + b"\x00"  # Change last byte
        corrupted_encrypted = base64.b64encode(corrupted_bytes).decode("utf-8")

        # Decryption should fail
        with pytest.raises(EncryptionException):
            encryption_service.decrypt_token(corrupted_encrypted, user_id)

    def test_key_rotation(self, encryption_service):
        """Test key rotation functionality."""
        user_id = "user_123"
        token = "test-token"

        # Encrypt with current version
        old_encrypted = encryption_service.encrypt_token(token, user_id)

        # Rotate key
        new_encrypted, new_version = encryption_service.rotate_user_key(
            user_id, old_encrypted
        )

        # New encrypted token should be different
        assert new_encrypted != old_encrypted
        assert new_version == 2  # KEY_VERSION + 1

        # New token should decrypt to same plaintext
        decrypted = encryption_service.decrypt_token(new_encrypted, user_id)
        assert decrypted == token

    def test_is_encrypted_detection(self, encryption_service):
        """Test encrypted token detection."""
        user_id = "user_123"
        plaintext_token = "plaintext-token"

        # Plaintext should not be detected as encrypted
        assert not encryption_service.is_encrypted(plaintext_token)

        # Encrypted token should be detected
        encrypted_token = encryption_service.encrypt_token(plaintext_token, user_id)
        assert encryption_service.is_encrypted(encrypted_token)

        # Invalid base64 should not be detected as encrypted
        assert not encryption_service.is_encrypted("invalid-token!!!")

        # Valid base64 but wrong format should not be detected
        wrong_format = base64.b64encode(b"wrong").decode("utf-8")
        assert not encryption_service.is_encrypted(wrong_format)

    def test_unsupported_key_version_warning(self, encryption_service, caplog):
        """Test handling of unsupported key versions."""
        user_id = "user_123"
        token = "test-token"

        # Create encrypted token with future version (99) using the key for that version
        future_version = 99
        key = encryption_service.derive_user_key(user_id, future_version)
        nonce = os.urandom(12)

        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, token.encode("utf-8"), None)

        # Package with unsupported version (99)
        encrypted_data = bytes([99]) + nonce + ciphertext
        encrypted_token = base64.b64encode(encrypted_data).decode("utf-8")

        # Should log warning and successfully decrypt using the version key
        with caplog.at_level("WARNING"):
            decrypted = encryption_service.decrypt_token(encrypted_token, user_id)
            assert decrypted == token
            assert "Unsupported key version" in caplog.text

    def test_encryption_randomness(self, encryption_service):
        """Test that encryption uses proper randomness."""
        user_id = "user_123"
        token = "test-token"

        # Encrypt same token multiple times
        encrypted1 = encryption_service.encrypt_token(token, user_id)
        encrypted2 = encryption_service.encrypt_token(token, user_id)
        encrypted3 = encryption_service.encrypt_token(token, user_id)

        # All encrypted tokens should be different (due to random nonce)
        assert encrypted1 != encrypted2
        assert encrypted2 != encrypted3
        assert encrypted1 != encrypted3

        # But all should decrypt to same plaintext
        decrypted1 = encryption_service.decrypt_token(encrypted1, user_id)
        decrypted2 = encryption_service.decrypt_token(encrypted2, user_id)
        decrypted3 = encryption_service.decrypt_token(encrypted3, user_id)

        assert decrypted1 == decrypted2 == decrypted3 == token

    def test_service_salt_error_handling(self):
        """Test error handling in service salt initialization."""
        # Mock settings that will cause base64 decode error
        bad_settings = Mock()
        bad_settings.token_encryption_salt = "invalid-base64!!!"

        with pytest.raises(EncryptionException) as exc_info:
            TokenEncryption(bad_settings)

        assert "Failed to initialize encryption service" in str(exc_info.value)

    def test_key_derivation_error_handling(self, encryption_service):
        """Test error handling in key derivation."""
        # Test with invalid user ID that might cause issues
        with patch(
            "services.user_management.security.encryption.PBKDF2HMAC"
        ) as mock_kdf:
            mock_kdf.side_effect = Exception("KDF error")

            with pytest.raises(EncryptionException) as exc_info:
                encryption_service.derive_user_key("user_123")

            assert "Failed to derive encryption key" in str(exc_info.value)

    def test_large_token_encryption(self, encryption_service):
        """Test encryption of large tokens."""
        user_id = "user_123"
        large_token = "x" * 10000  # 10KB token

        encrypted = encryption_service.encrypt_token(large_token, user_id)
        decrypted = encryption_service.decrypt_token(encrypted, user_id)

        assert decrypted == large_token

    def test_unicode_token_encryption(self, encryption_service):
        """Test encryption of tokens with unicode characters."""
        user_id = "user_123"
        unicode_token = "token-with-ünïcödé-🔑"

        encrypted = encryption_service.encrypt_token(unicode_token, user_id)
        decrypted = encryption_service.decrypt_token(encrypted, user_id)

        assert decrypted == unicode_token

    def test_concurrent_encryption_safety(self, encryption_service):
        """Test that concurrent encryption operations are safe."""
        import threading
        import time

        user_id = "user_123"
        token = "concurrent-token"
        results = []
        errors = []

        def encrypt_decrypt():
            try:
                encrypted = encryption_service.encrypt_token(token, user_id)
                time.sleep(0.01)  # Small delay to increase concurrency
                decrypted = encryption_service.decrypt_token(encrypted, user_id)
                results.append(decrypted)
            except Exception as e:
                errors.append(e)

        # Run multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=encrypt_decrypt)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All operations should succeed
        assert len(errors) == 0
        assert len(results) == 10
        assert all(result == token for result in results)
