"""
UUID models used across all services.
"""

import uuid
from typing import Any

from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema


class UUID4(str):
    """UUID4 string type for Pydantic models."""

    def __new__(cls, value: str) -> "UUID4":
        """Create a new UUID4 instance with proper string value."""
        if not isinstance(value, str):
            raise ValueError("UUID4 must be a string")

        # Validate that it's a valid UUID4
        try:
            parsed_uuid = uuid.UUID(value)
            if parsed_uuid.version != 4:
                raise ValueError(
                    f"UUID must be version 4, got version {parsed_uuid.version}"
                )
        except ValueError as e:
            raise ValueError(f"Invalid UUID4 format: {e}")

        # Create the string instance with the validated value
        return super().__new__(cls, value)

    def __init__(self, value: str) -> None:
        """Initialize UUID4 (no-op since __new__ handles everything)."""
        # The value is already set in __new__, so we don't need to do anything here
        pass

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetJsonSchemaHandler,
    ) -> CoreSchema:
        """Get Pydantic core schema for UUID4."""
        return core_schema.json_schema(
            core_schema.str_schema(
                min_length=36,
                max_length=36,
                pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
            )
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        """Get JSON schema for UUID4."""
        return {
            "type": "string",
            "format": "uuid",
            "minLength": 36,
            "maxLength": 36,
            "pattern": r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        }

    @classmethod
    def generate(cls) -> "UUID4":
        """Generate a new UUID4."""
        return cls(str(uuid.uuid4()))
