"""
Settings base class to replace pydantic_settings.

This module provides a mockable alternative to pydantic_settings that
allows for easier testing while maintaining similar functionality.
"""

import os
from abc import ABC
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union, get_type_hints


T = TypeVar("T", bound="BaseSettings")


class FieldInfo:
    """Information about a field in a settings class."""
    
    def __init__(
        self,
        default: Any = None,
        description: str = "",
        validation_alias: Optional[Union[str, list]] = None,
        required: bool = False,
    ):
        self.default = default
        self.description = description
        self.validation_alias = validation_alias
        self.required = required


def Field(
    default: Any = None,
    *,
    description: str = "",
    validation_alias: Optional[Union[str, list]] = None,
    **kwargs
) -> Any:
    """Create a field descriptor for settings."""
    # Handle the ellipsis (...) which indicates a required field
    required = default is ...
    if required:
        default = None
    
    return FieldInfo(
        default=default,
        description=description,
        validation_alias=validation_alias,
        required=required,
    )


class SettingsConfigDict:
    """Configuration for settings loading."""
    
    def __init__(
        self,
        env_file: Optional[str] = None,
        env_file_encoding: str = "utf-8",
        case_sensitive: bool = True,
        extra: str = "forbid",
    ):
        self.env_file = env_file
        self.env_file_encoding = env_file_encoding
        self.case_sensitive = case_sensitive
        self.extra = extra


class BaseSettings(ABC):
    """Base class for settings that loads from environment variables."""
    
    model_config: SettingsConfigDict = SettingsConfigDict()
    
    def __init__(self, **kwargs):
        """Initialize settings by loading from environment and .env file."""
        # Load from .env file if specified
        env_vars = {}
        if hasattr(self, 'model_config') and self.model_config.env_file:
            env_vars = self._load_env_file(self.model_config.env_file)
        
        # Get class annotations and defaults
        annotations = get_type_hints(self.__class__)
        
        # Process each field
        for field_name, field_type in annotations.items():
            if field_name.startswith('_'):
                continue
                
            # Get field info if it exists
            field_info = getattr(self.__class__, field_name, None)
            if isinstance(field_info, FieldInfo):
                default_value = field_info.default
                validation_alias = field_info.validation_alias
                required = field_info.required
            else:
                default_value = field_info
                validation_alias = None
                required = False
            
            # Try to get value from various sources in order of priority:
            # 1. Keyword arguments
            # 2. Environment variables (with aliases)
            # 3. .env file
            # 4. Default value
            
            value = None
            
            # 1. Check kwargs first
            if field_name in kwargs:
                value = kwargs[field_name]
            else:
                # 2. Check environment variables
                env_names = []
                if validation_alias:
                    if isinstance(validation_alias, AliasChoices):
                        env_names.extend(validation_alias.choices)
                    elif isinstance(validation_alias, list):
                        env_names.extend(validation_alias)
                    else:
                        env_names.append(validation_alias)
                
                # Add the field name itself (converted to uppercase)
                env_names.append(field_name.upper())
                
                # Handle case sensitivity
                if not getattr(self.model_config, 'case_sensitive', True):
                    env_names.extend([name.lower() for name in env_names])
                
                for env_name in env_names:
                    if env_name in os.environ:
                        value = os.environ[env_name]
                        break
                    # Also check .env file variables
                    elif env_name in env_vars:
                        value = env_vars[env_name]
                        break
                
                # 3. Use default if no value found
                if value is None:
                    if required:
                        raise ValueError(f"Required field '{field_name}' not found in environment")
                    value = default_value
            
            # Convert value to correct type
            if value is not None:
                value = self._convert_value(value, field_type)
            
            # Set the attribute
            setattr(self, field_name, value)
    
    def _load_env_file(self, env_file_path: str) -> Dict[str, str]:
        """Load environment variables from a .env file."""
        env_vars = {}
        env_path = Path(env_file_path)
        
        if env_path.exists():
            with open(env_path, 'r', encoding=getattr(self.model_config, 'env_file_encoding', 'utf-8')) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
        
        return env_vars
    
    def _convert_value(self, value: Any, target_type: Type) -> Any:
        """Convert a string value to the target type."""
        if value is None:
            return None
        
        # Handle string conversion - skip type check for generic types
        if not isinstance(value, str):
            return value
        
        # Handle boolean conversion
        if target_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        
        # Handle integer conversion
        if target_type == int:
            return int(value)
        
        # Handle float conversion
        if target_type == float:
            return float(value)
        
        # Handle list conversion (simple comma-separated)
        if hasattr(target_type, '__origin__') and target_type.__origin__ == list:
            if value.startswith('[') and value.endswith(']'):
                # Handle JSON-like list format
                import json
                return json.loads(value)
            else:
                # Handle comma-separated format
                return [item.strip() for item in value.split(',') if item.strip()]
        
        # For Optional types, extract the inner type
        if hasattr(target_type, '__origin__') and target_type.__origin__ == Union:
            # Get the non-None type from Optional[Type]
            args = target_type.__args__
            non_none_types = [arg for arg in args if arg != type(None)]
            if non_none_types:
                return self._convert_value(value, non_none_types[0])
        
        # Return as string for any other type
        return value


# Compatibility classes for easier migration
class AliasChoices:
    """Helper class to provide multiple environment variable aliases."""
    
    def __init__(self, *choices):
        self.choices = list(choices)
    
    def __iter__(self):
        return iter(self.choices) 