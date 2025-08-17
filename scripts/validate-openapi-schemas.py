#!/usr/bin/env python3
"""
Validate OpenAPI schemas against OpenAPI 3.0 specification.

This script validates that all generated OpenAPI schemas conform to the OpenAPI 3.0 spec.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def validate_openapi_3_0_structure(schema: Dict[str, Any]) -> List[str]:
    """Validate basic OpenAPI 3.0 structure requirements."""
    errors = []
    
    # Check required top-level fields
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in schema:
            errors.append(f"Missing required field: {field}")
    
    # Check OpenAPI version
    if "openapi" in schema:
        version = schema["openapi"]
        if not version.startswith("3."):
            errors.append(f"Invalid OpenAPI version: {version}. Must be 3.x")
    
    # Check info object
    if "info" in schema:
        info = schema["info"]
        info_required = ["title", "version"]
        for field in info_required:
            if field not in info:
                errors.append(f"Missing required info field: {field}")
    
    # Check paths object
    if "paths" in schema:
        if not isinstance(schema["paths"], dict):
            errors.append("Paths must be an object")
        else:
            for path, path_item in schema["paths"].items():
                if not path.startswith("/"):
                    errors.append(f"Path must start with '/': {path}")
                
                # Check that path has at least one HTTP method
                http_methods = ["get", "post", "put", "delete", "patch", "head", "options", "trace"]
                has_method = any(method in path_item for method in http_methods)
                if not has_method:
                    errors.append(f"Path {path} must have at least one HTTP method")
    
    return errors

def validate_schema_components(schema: Dict[str, Any]) -> List[str]:
    """Validate schema components and references."""
    errors = []
    
    # Check components if present
    if "components" in schema:
        components = schema["components"]
        
        # Check schemas
        if "schemas" in components:
            schemas = components["schemas"]
            for schema_name, schema_def in schemas.items():
                if not isinstance(schema_def, dict):
                    errors.append(f"Schema {schema_name} must be an object")
                    continue
                
                # Check required schema fields
                if "type" not in schema_def:
                    errors.append(f"Schema {schema_name} missing 'type' field")
                
                # Check properties if type is object
                if schema_def.get("type") == "object" and "properties" in schema_def:
                    properties = schema_def["properties"]
                    if not isinstance(properties, dict):
                        errors.append(f"Schema {schema_name} properties must be an object")
    
    return errors

def validate_path_operations(schema: Dict[str, Any]) -> List[str]:
    """Validate path operations and their structure."""
    errors = []
    
    if "paths" not in schema:
        return errors
    
    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method.lower() in ["get", "post", "put", "delete", "patch", "head", "options", "trace"]:
                # Check operation has responses
                if "responses" not in operation:
                    errors.append(f"Operation {method.upper()} {path} missing responses")
                else:
                    responses = operation["responses"]
                    # Check for at least one response
                    if not responses:
                        errors.append(f"Operation {method.upper()} {path} has no responses")
                    
                    # Check for at least one successful response (2xx or default)
                    has_success = any(
                        code.startswith("2") or code == "default" 
                        for code in responses.keys()
                    )
                    if not has_success:
                        errors.append(f"Operation {method.upper()} {path} should have at least one successful response")
    
    return errors

def validate_schema_file(schema_file: Path) -> Dict[str, Any]:
    """Validate a single OpenAPI schema file."""
    print(f"🔍 Validating {schema_file.name}...")
    
    try:
        with open(schema_file, 'r') as f:
            schema = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "file": schema_file.name,
            "valid": False,
            "errors": [f"Invalid JSON: {e}"]
        }
    except Exception as e:
        return {
            "file": schema_file.name,
            "valid": False,
            "errors": [f"File read error: {e}"]
        }
    
    # Run all validations
    all_errors = []
    all_errors.extend(validate_openapi_3_0_structure(schema))
    all_errors.extend(validate_schema_components(schema))
    all_errors.extend(validate_path_operations(schema))
    
    return {
        "file": schema_file.name,
        "valid": len(all_errors) == 0,
        "errors": all_errors,
        "schema": schema
    }

def main():
    """Validate all OpenAPI schema files."""
    print("🔍 Validating OpenAPI schemas against OpenAPI 3.0 specification...\n")
    
    # Find all schema files
    schemas_dir = Path(__file__).parent.parent / "openapi-schemas"
    if not schemas_dir.exists():
        print(f"❌ Schemas directory not found: {schemas_dir}")
        return 1
    
    schema_files = list(schemas_dir.glob("*-openapi.json"))
    if not schema_files:
        print(f"❌ No OpenAPI schema files found in {schemas_dir}")
        return 1
    
    print(f"📁 Found {len(schema_files)} schema files to validate\n")
    
    # Validate each schema
    results = []
    for schema_file in schema_files:
        result = validate_schema_file(schema_file)
        results.append(result)
        
        if result["valid"]:
            print(f"✅ {result['file']}: Valid")
        else:
            print(f"❌ {result['file']}: Invalid")
            for error in result["errors"][:3]:  # Show first 3 errors
                print(f"   - {error}")
            if len(result["errors"]) > 3:
                print(f"   ... and {len(result['errors']) - 3} more errors")
    
    # Summary
    print("\n" + "="*60)
    print("📊 OPENAPI VALIDATION RESULTS")
    print("="*60)
    
    valid_count = sum(1 for r in results if r["valid"])
    total_count = len(results)
    
    for result in results:
        status_icon = "✅" if result["valid"] else "❌"
        print(f"{status_icon} {result['file']}: {'Valid' if result['valid'] else 'Invalid'}")
    
    print(f"\n🎯 Validation Success Rate: {valid_count}/{total_count} ({valid_count/total_count*100:.1f}%)")
    
    if valid_count == total_count:
        print("🎉 All OpenAPI schemas are valid!")
        return 0
    else:
        print("⚠️  Some OpenAPI schemas have validation errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
