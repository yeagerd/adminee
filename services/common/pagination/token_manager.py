"""
Token manager for cursor-based pagination.

This module handles secure token generation, validation, and management for
cursor-based pagination using the itsdangerous library.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from itsdangerous import URLSafeSerializer, BadSignature, SignatureExpired


class TokenManager:
    """
    Manages secure token operations for cursor-based pagination.
    
    This class handles the encoding, decoding, and validation of cursor tokens
    using the itsdangerous library for security.
    """
    
    def __init__(self, secret_key: str, token_expiry: int = 3600):
        """
        Initialize the token manager.
        
        Args:
            secret_key: Secret key for token signing
            token_expiry: Token expiration time in seconds (default: 1 hour)
        """
        self.secret_key = secret_key
        self.token_expiry = token_expiry
        self.serializer = URLSafeSerializer(secret_key)
    
    def encode_token(self, data: Dict[str, Any]) -> str:
        """
        Encode data into a secure, URL-safe token.
        
        Args:
            data: Dictionary of data to encode
            
        Returns:
            URL-safe encoded token string
        """
        # Add timestamp for expiration checking
        token_data = {
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=self.token_expiry)).isoformat()
        }
        
        # Serialize to JSON and encode
        json_data = json.dumps(token_data, separators=(',', ':'))
        return self.serializer.dumps(json_data)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode a token back to the original data.
        
        Args:
            token: Encoded token string
            
        Returns:
            Original data dictionary
            
        Raises:
            BadSignature: If token signature is invalid
            SignatureExpired: If token has expired
            ValueError: If token data is malformed
        """
        try:
            # Decode the token
            json_data = self.serializer.loads(token)
            token_data = json.loads(json_data)
            
            # Check expiration
            expires_at_str = token_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if datetime.now(timezone.utc) > expires_at:
                    raise SignatureExpired("Token has expired")
            
            # Return the original data
            return token_data.get("data", {})
            
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid token format: {e}")
    
    def validate_token(self, token: str) -> bool:
        """
        Validate if a token is valid and not expired.
        
        Args:
            token: Encoded token string
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self.decode_token(token)
            return True
        except (BadSignature, SignatureExpired, ValueError):
            return False
    
    def get_token_age(self, token: str) -> Optional[timedelta]:
        """
        Get the age of a token.
        
        Args:
            token: Encoded token string
            
        Returns:
            Token age as timedelta, or None if invalid
        """
        try:
            json_data = self.serializer.loads(token)
            token_data = json.loads(json_data)
            
            created_at_str = token_data.get("created_at")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                return datetime.now(timezone.utc) - created_at
            
            return None
        except (BadSignature, json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token has expired.
        
        Args:
            token: Encoded token string
            
        Returns:
            True if expired, False otherwise
        """
        try:
            json_data = self.serializer.loads(token)
            token_data = json.loads(json_data)
            
            expires_at_str = token_data.get("expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                return datetime.now(timezone.utc) > expires_at
            
            return False
        except (BadSignature, json.JSONDecodeError, KeyError, ValueError):
            return True
    
    def rotate_secret_key(self, new_secret_key: str) -> None:
        """
        Rotate the secret key used for token signing.
        
        Args:
            new_secret_key: New secret key to use
        """
        self.secret_key = new_secret_key
        self.serializer = URLSafeSerializer(new_secret_key)
    
    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a token without decoding the data.
        
        Args:
            token: Encoded token string
            
        Returns:
            Token metadata dictionary, or None if invalid
        """
        try:
            json_data = self.serializer.loads(token)
            token_data = json.loads(json_data)
            
            return {
                "created_at": token_data.get("created_at"),
                "expires_at": token_data.get("expires_at"),
                "is_expired": self.is_token_expired(token),
                "age": self.get_token_age(token)
            }
        except (BadSignature, json.JSONDecodeError, KeyError, ValueError):
            return None 