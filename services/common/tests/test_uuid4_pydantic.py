"""
Tests for UUID4 Pydantic schema generation.
"""

import pytest
from pydantic import BaseModel, ValidationError

from services.api.v1.common.models.uuid import UUID4


class TestModel(BaseModel):
    """Test model using UUID4."""
    id: UUID4


class TestUUID4PydanticSchema:
    """Test UUID4 Pydantic schema functionality."""

    def test_pydantic_model_creation_with_valid_uuid4(self):
        """Test that a Pydantic model can be created with a valid UUID4."""
        valid_uuid4 = "550e8400-e29b-41d4-a716-446655440000"
        
        model = TestModel(id=valid_uuid4)
        # Pydantic validation passes, but the value remains a string
        # The UUID4 class is used for type annotation, not runtime validation
        assert isinstance(model.id, str)
        assert str(model.id) == valid_uuid4

    def test_pydantic_model_creation_with_invalid_uuid(self):
        """Test that a Pydantic model rejects invalid UUIDs based on schema constraints."""
        invalid_uuid = "not-a-uuid"
        
        with pytest.raises(ValidationError) as exc_info:
            TestModel(id=invalid_uuid)
        
        # Pydantic validates against the schema (length and pattern), not our custom logic
        assert "String should have at least 36 characters" in str(exc_info.value)

    def test_pydantic_model_creation_with_wrong_version(self):
        """Test that a Pydantic model rejects non-version-4 UUIDs based on pattern."""
        # Create a UUID1 (timestamp-based) instead of UUID4
        import uuid
        uuid1_string = str(uuid.uuid1())
        
        with pytest.raises(ValidationError) as exc_info:
            TestModel(id=uuid1_string)
        
        # Pydantic validates against the pattern, which requires version 4 format
        assert "String should match pattern" in str(exc_info.value)

    def test_pydantic_model_creation_with_non_string(self):
        """Test that a Pydantic model rejects non-string inputs."""
        with pytest.raises(ValidationError) as exc_info:
            TestModel(id=123)
        
        # Pydantic validates the type first
        assert "Input should be a valid string" in str(exc_info.value)

    def test_pydantic_schema_generation(self):
        """Test that Pydantic generates the correct schema for UUID4."""
        schema = TestModel.model_json_schema()
        
        # Check that the id field has the correct schema
        id_field = schema["properties"]["id"]
        assert id_field["type"] == "string"
        assert id_field["format"] == "uuid"
        assert id_field["minLength"] == 36
        assert id_field["maxLength"] == 36
        assert "pattern" in id_field

    def test_uuid4_inheritance_behavior(self):
        """Test that UUID4 instances behave like strings in Pydantic."""
        valid_uuid4 = "550e8400-e29b-41d4-a716-446655440000"
        
        model = TestModel(id=valid_uuid4)
        
        # Should behave like a string
        assert len(model.id) == 36
        assert model.id.startswith("550e8400")
        assert model.id.endswith("446655440000")
        assert model.id.upper() == valid_uuid4.upper()

    def test_uuid4_direct_instantiation(self):
        """Test that UUID4 class works correctly when instantiated directly."""
        valid_uuid4 = "550e8400-e29b-41d4-a716-446655440000"
        
        # Direct instantiation should use our custom validation
        uuid4_instance = UUID4(valid_uuid4)
        assert isinstance(uuid4_instance, UUID4)
        assert str(uuid4_instance) == valid_uuid4

    def test_uuid4_direct_instantiation_invalid(self):
        """Test that UUID4 class rejects invalid UUIDs when instantiated directly."""
        invalid_uuid = "not-a-uuid"
        
        with pytest.raises(ValueError, match="Invalid UUID4 format"):
            UUID4(invalid_uuid)

    def test_uuid4_direct_instantiation_wrong_version(self):
        """Test that UUID4 class rejects wrong version UUIDs when instantiated directly."""
        import uuid
        uuid1_string = str(uuid.uuid1())
        
        with pytest.raises(ValueError, match="UUID must be version 4"):
            UUID4(uuid1_string)
