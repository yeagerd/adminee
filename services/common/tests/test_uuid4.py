"""
Tests for UUID4 class.
"""

import uuid

import pytest

from services.api.v1.common.models.uuid import UUID4


class TestUUID4:
    """Test UUID4 class functionality."""

    def test_uuid4_creation_with_valid_uuid4(self):
        """Test creating UUID4 with a valid UUID4 string."""
        valid_uuid4 = str(uuid.uuid4())
        uuid4_instance = UUID4(valid_uuid4)

        # Should store the value correctly
        assert str(uuid4_instance) == valid_uuid4
        assert len(uuid4_instance) == 36

    def test_uuid4_creation_with_invalid_uuid(self):
        """Test creating UUID4 with an invalid UUID string."""
        invalid_uuid = "not-a-uuid"

        with pytest.raises(ValueError, match="Invalid UUID4 format"):
            UUID4(invalid_uuid)

    def test_uuid4_creation_with_wrong_version(self):
        """Test creating UUID4 with a UUID that's not version 4."""
        # Create a UUID1 (timestamp-based) instead of UUID4
        uuid1_instance = uuid.uuid1()
        uuid1_string = str(uuid1_instance)

        with pytest.raises(
            ValueError,
            match=f"UUID must be version 4, got version {uuid1_instance.version}",
        ):
            UUID4(uuid1_string)

    def test_uuid4_creation_with_non_string(self):
        """Test creating UUID4 with non-string input."""
        with pytest.raises(ValueError, match="UUID4 must be a string"):
            UUID4(123)

        with pytest.raises(ValueError, match="UUID4 must be a string"):
            UUID4(None)

    def test_uuid4_generate(self):
        """Test UUID4.generate() method."""
        generated_uuid4 = UUID4.generate()

        # Should be a valid UUID4 instance
        assert isinstance(generated_uuid4, UUID4)
        assert len(generated_uuid4) == 36

        # Should be version 4
        parsed_uuid = uuid.UUID(str(generated_uuid4))
        assert parsed_uuid.version == 4

    def test_uuid4_string_operations(self):
        """Test that UUID4 instances work like regular strings."""
        valid_uuid4 = str(uuid.uuid4())
        uuid4_instance = UUID4(valid_uuid4)

        # String operations should work
        assert uuid4_instance.startswith(valid_uuid4[:8])
        assert uuid4_instance.endswith(valid_uuid4[-12:])
        assert uuid4_instance.replace("-", "") == valid_uuid4.replace("-", "")

        # Should be hashable and comparable
        assert hash(uuid4_instance) == hash(valid_uuid4)
        assert uuid4_instance == valid_uuid4
        assert uuid4_instance == UUID4(valid_uuid4)

    def test_uuid4_immutability(self):
        """Test that UUID4 instances are immutable like strings."""
        valid_uuid4 = str(uuid.uuid4())
        uuid4_instance = UUID4(valid_uuid4)

        # String methods should return new instances
        upper_instance = uuid4_instance.upper()
        assert upper_instance != uuid4_instance
        assert isinstance(upper_instance, str)
        assert not isinstance(upper_instance, UUID4)

        # The original instance should remain unchanged
        assert str(uuid4_instance) == valid_uuid4
