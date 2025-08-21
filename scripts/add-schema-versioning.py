#!/usr/bin/env python3
"""
Add version metadata to OpenAPI schemas.

This script adds version information to OpenAPI schemas to enable
versioning and compatibility tracking.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_git_info(schema_path: Path) -> Dict[str, Any]:
    """Get Git information for versioning."""
    import subprocess
    
    try:
        # Get the last commit that modified this schema
        result = subprocess.run(
            ['git', 'log', '--format=%H|%an|%ad|%s', '--date=iso', '-1', '--', str(schema_path)],
            capture_output=True, text=True, cwd=project_root
        )
        
        if result.returncode == 0 and result.stdout.strip():
            commit_hash, author, date, subject = result.stdout.strip().split('|', 3)
            return {
                'commit_hash': commit_hash,
                'author': author,
                'date': date,
                'subject': subject
            }
    except Exception:
        pass
    
    return {}

def add_version_metadata(schema: Dict[str, Any], service_name: str, schema_path: Path) -> Dict[str, Any]:
    """Add version metadata to OpenAPI schema."""
    
    # Get Git information
    git_info = get_git_info(schema_path)
    
    # Add version metadata
    if 'info' not in schema:
        schema['info'] = {}
    
    # Add version information
    schema['info']['version'] = f"1.0.0-{datetime.now().strftime('%Y%m%d')}"
    schema['info']['title'] = f"{service_name.title()} Service API"
    schema['info']['description'] = f"OpenAPI schema for {service_name} service"
    
    # Add custom version metadata
    if 'x-version-info' not in schema:
        schema['x-version-info'] = {}
    
    schema['x-version-info'].update({
        'service_name': service_name,
        'generated_at': datetime.now().isoformat(),
        'schema_file': str(schema_path.relative_to(project_root)),
        'git_info': git_info
    })
    
    # Add compatibility information
    if 'x-compatibility' not in schema:
        schema['x-compatibility'] = {
            'breaking_changes': [],
            'deprecated_endpoints': [],
            'migration_notes': [],
            'supported_versions': ['1.0.0']
        }
    
    return schema

def process_schema_file(schema_path: Path, service_name: str) -> bool:
    """Process a single schema file."""
    try:
        # Read existing schema
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        
        # Add version metadata
        updated_schema = add_version_metadata(schema, service_name, schema_path)
        
        # Write updated schema
        with open(schema_path, 'w') as f:
            json.dump(updated_schema, f, indent=2)
        
        print(f"✅ Added version metadata to {schema_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to process {schema_path}: {e}")
        return False

def main():
    """Main function to process all schema files."""
    print("🔧 Adding version metadata to OpenAPI schemas...")
    
    # Find all schema files
    schema_files = []
    for service_dir in project_root.glob('services/*/'):
        schema_path = service_dir / 'openapi' / 'schema.json'
        if schema_path.exists():
            service_name = service_dir.name
            schema_files.append((schema_path, service_name))
    
    if not schema_files:
        print("⚠️  No schema files found")
        return
    
    print(f"Found {len(schema_files)} schema files:")
    for schema_path, service_name in schema_files:
        print(f"  - {service_name}: {schema_path}")
    
    print("\nProcessing schemas...")
    
    successful = 0
    total = len(schema_files)
    
    for schema_path, service_name in schema_files:
        if process_schema_file(schema_path, service_name):
            successful += 1
    
    print(f"\n✅ Version metadata added to {successful}/{total} schemas")
    
    if successful == total:
        print("🎉 All schemas updated successfully!")
    else:
        print("⚠️  Some schemas failed to update")

if __name__ == '__main__':
    main()
