"""
Token encryption implementation for User Management Service.

Provides secure encryption and decryption of OAuth tokens and sensitive data
using AES-256-GCM encryption with user-specific keys derived via PBKDF2.
"""

import base64
import os
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from services.common.config_secrets import (
    get_token_encryption_salt,  # type: ignore[misc]
)
from services.common.http_errors import ServiceError
from services.common.logging_config import get_logger
from services.user.settings import Settings

# Set up logging
logger = get_logger(__name__)

# Constants
KEY_LENGTH = 32  # 256 bits for AES-256
SALT_LENGTH = 16  # 128 bits
NONCE_LENGTH = 12  # 96 bits for GCM
TAG_LENGTH = 16  # 128 bits for GCM authentication tag
PBKDF2_ITERATIONS = 100000  # OWASP recommended minimum
KEY_VERSION = 1  # For key rotation support


class TokenEncryption:
    """
    Token encryption service using AES-256-GCM with user-specific keys.

    Features:
    - User-specific encryption keys derived from user ID and service salt
    - AES-256-GCM authenticated encryption for integrity and confidentiality
    - PBKDF2 key derivation with configurable iterations
    - Key versioning for rotation support
    - Secure random salt and nonce generation
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the token encryption service.

        Args:
            settings: Application settings for encryption configuration
        """
        self.settings = settings or Settings()
        self._service_salt = self._get_service_salt()
        logger.info("Token encryption service initialized", key_version=KEY_VERSION)

    def _get_service_salt(self) -> bytes:
        """
        Get or generate the service-wide salt for key derivation.

        Returns:
            Service salt as bytes

        Raises:
            ServiceError: If salt cannot be obtained
        """
        try:
            # Use config_secrets which respects environment-based priority:
            # - Local: env vars/.env files
            # - Production: Secret Manager first, then env vars
            salt_b64 = get_token_encryption_salt()
            if not salt_b64:
                logger.error(
                    "Failed to get service salt - TOKEN_ENCRYPTION_SALT environment variable not set"
                )
                raise ServiceError("Failed to initialize encryption service")

            # Validate base64 encoding
            try:
                salt_bytes = base64.b64decode(salt_b64)
            except Exception as decode_error:
                logger.error(
                    "Failed to decode service salt - invalid base64 format",
                    error=str(decode_error),
                )
                raise ServiceError("Failed to initialize encryption service")

            # Validate salt length (should be at least 16 bytes)
            if len(salt_bytes) < 16:
                logger.error(
                    "Service salt too short - must be at least 16 bytes",
                    salt_length=len(salt_bytes),
                )
                raise ServiceError("Failed to initialize encryption service")

            return salt_bytes

        except ServiceError:
            # Re-raise ServiceError as-is
            raise
        except Exception as e:
            logger.error("Failed to get service salt", error=str(e))
            raise ServiceError("Failed to initialize encryption service")

    def derive_user_key(self, user_id: str, version: int = KEY_VERSION) -> bytes:
        """
        Derive a user-specific encryption key using PBKDF2.

        Args:
            user_id: User identifier for key derivation
            version: Key version for rotation support

        Returns:
            32-byte encryption key

        Raises:
            ServiceError: If key derivation fails
        """
        try:
            logger.debug("Deriving user key", user_id=user_id, version=version)

            # Create user-specific salt by combining service salt with user ID and version
            version_bytes = f"{user_id}:{version}".encode("utf-8")
            user_salt = self._service_salt + version_bytes
            # Hash to ensure consistent length and distribution
            import hashlib

            user_salt = hashlib.sha256(user_salt).digest()[:SALT_LENGTH]

            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=KEY_LENGTH,
                salt=user_salt,
                iterations=PBKDF2_ITERATIONS,
            )

            # Use user ID as password input
            password = user_id.encode("utf-8")
            key = kdf.derive(password)

            logger.debug("Successfully derived user key", user_id=user_id)
            return key

        except Exception as e:
            logger.error("Key derivation failed", user_id=user_id, error=str(e))
            raise ServiceError(f"Failed to derive encryption key for user {user_id}")

    def encrypt_token(
        self, token: str, user_id: str, additional_data: Optional[str] = None
    ) -> str:
        """
        Encrypt a token using user-specific key and AES-256-GCM.

        Args:
            token: Token string to encrypt
            user_id: User ID for key derivation
            additional_data: Optional additional authenticated data

        Returns:
            Base64-encoded encrypted token with embedded metadata

        Raises:
            ServiceError: If encryption fails
        """
        try:
            logger.debug("Encrypting token", user_id=user_id)

            if not token:
                raise ValueError("Token cannot be empty")

            # Derive user-specific key
            key = self.derive_user_key(user_id)

            # Generate random nonce
            nonce = os.urandom(NONCE_LENGTH)

            # Initialize AES-GCM cipher
            aesgcm = AESGCM(key)

            # Prepare additional authenticated data
            aad = additional_data.encode("utf-8") if additional_data else None

            # Encrypt token
            ciphertext = aesgcm.encrypt(nonce, token.encode("utf-8"), aad)

            # Package: version(1) + nonce(12) + ciphertext+tag
            encrypted_data = bytes([KEY_VERSION]) + nonce + ciphertext

            # Encode as base64 for storage
            encrypted_b64 = base64.b64encode(encrypted_data).decode("utf-8")

            logger.info("Token encrypted successfully", user_id=user_id)
            return encrypted_b64

        except Exception as e:
            logger.error("Token encryption failed", user_id=user_id, error=str(e))
            raise ServiceError(f"Failed to encrypt token for user {user_id}")

    def decrypt_token(
        self, encrypted_token: str, user_id: str, additional_data: Optional[str] = None
    ) -> str:
        """
        Decrypt a token using user-specific key and AES-256-GCM.

        Args:
            encrypted_token: Base64-encoded encrypted token
            user_id: User ID for key derivation
            additional_data: Optional additional authenticated data

        Returns:
            Decrypted token string

        Raises:
            ServiceError: If decryption fails
        """
        try:
            logger.debug("Decrypting token", user_id=user_id)

            if not encrypted_token:
                raise ValueError("Encrypted token cannot be empty")

            # Decode from base64
            try:
                encrypted_data = base64.b64decode(encrypted_token)
            except Exception as e:
                raise ValueError(f"Invalid base64 encoding: {e}")

            # Validate minimum length: version(1) + nonce(12) + tag(16) = 29
            if len(encrypted_data) < 29:
                raise ValueError("Encrypted data too short")

            # Extract components
            version = encrypted_data[0]
            nonce = encrypted_data[1 : 1 + NONCE_LENGTH]
            ciphertext = encrypted_data[1 + NONCE_LENGTH :]

            # Validate version
            if version != KEY_VERSION:
                logger.warning(
                    "Unsupported key version", version=version, user_id=user_id
                )
                # For now, try to decrypt with current version
                # In production, implement key rotation logic

            # Derive user-specific key (using version from encrypted data)
            key = self.derive_user_key(user_id, version)

            # Initialize AES-GCM cipher
            aesgcm = AESGCM(key)

            # Prepare additional authenticated data
            aad = additional_data.encode("utf-8") if additional_data else None

            # Decrypt token
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)

            # Decode to string
            token = plaintext.decode("utf-8")

            logger.debug("Token decrypted successfully", user_id=user_id)
            return token

        except Exception as e:
            logger.error("Token decryption failed", user_id=user_id, error=str(e))
            raise ServiceError(f"Failed to decrypt token for user {user_id}")

    def rotate_user_key(self, user_id: str, old_token: str) -> Tuple[str, int]:
        """
        Rotate encryption key for a user by re-encrypting with new version.

        Args:
            user_id: User ID for key rotation
            old_token: Encrypted token to migrate

        Returns:
            Tuple of (new_encrypted_token, new_version)

        Raises:
            ServiceError: If key rotation fails
        """
        try:
            logger.info("Rotating user key", user_id=user_id)

            # Decrypt with old key
            decrypted_token = self.decrypt_token(old_token, user_id)

            # Re-encrypt with new version
            new_version = KEY_VERSION + 1
            new_key = self.derive_user_key(user_id, new_version)

            # Generate new nonce
            nonce = os.urandom(NONCE_LENGTH)

            # Encrypt with new key
            aesgcm = AESGCM(new_key)
            ciphertext = aesgcm.encrypt(nonce, decrypted_token.encode("utf-8"), None)

            # Package with new version
            encrypted_data = bytes([new_version]) + nonce + ciphertext
            new_encrypted_token = base64.b64encode(encrypted_data).decode("utf-8")

            logger.info(
                "User key rotated successfully",
                user_id=user_id,
                new_version=new_version,
            )
            return new_encrypted_token, new_version

        except Exception as e:
            logger.error("Key rotation failed", user_id=user_id, error=str(e))
            raise ServiceError(f"Failed to rotate key for user {user_id}")

    def is_encrypted(self, token: str) -> bool:
        """
        Check if a token string appears to be encrypted.

        Args:
            token: Token string to check

        Returns:
            True if token appears encrypted, False otherwise
        """
        try:
            # Try to decode as base64
            data = base64.b64decode(token)

            # Check minimum length and version byte
            if len(data) >= 29 and data[0] in [KEY_VERSION]:
                return True

        except Exception:
            pass

        return False
