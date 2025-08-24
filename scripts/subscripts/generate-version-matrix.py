#!/usr/bin/env python3
"""
Generate version compatibility matrix from OpenAPI schemas.

This script analyzes versioned schemas to create a compatibility matrix
and detect potential breaking changes.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Set
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_schema(schema_path: Path) -> Dict[str, Any]:
    """Load a schema file."""
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load {schema_path}: {e}")
        return {}

def extract_endpoints(schema: Dict[str, Any]) -> Set[str]:
    """Extract endpoint paths from schema."""
    endpoints = set()
    
    if 'paths' in schema:
        for path, methods in schema['paths'].items():
            for method in methods:
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    endpoints.add(f"{method.upper()} {path}")
    
    return endpoints

def extract_models(schema: Dict[str, Any]) -> Set[str]:
    """Extract model names from schema."""
    models = set()
    
    if 'components' in schema and 'schemas' in schema['components']:
        models.update(schema['components']['schemas'].keys())
    
    return models

def analyze_schema_changes(schemas: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze schema changes and create compatibility matrix."""
    
    analysis = {
        'generated_at': datetime.now().isoformat(),
        'services': {},
        'compatibility_matrix': {},
        'breaking_changes': [],
        'deprecated_endpoints': [],
        'new_features': [],
        'summary': {}
    }
    
    # Analyze each service
    for service_name, schema in schemas.items():
        if not schema:
            continue
            
        service_info = {
            'version': schema.get('info', {}).get('version', 'unknown'),
            'title': schema.get('info', {}).get('title', 'Unknown'),
            'endpoints': extract_endpoints(schema),
            'models': extract_models(schema),
            'version_info': schema.get('x-version-info', {}),
            'compatibility': schema.get('x-compatibility', {})
        }
        
        analysis['services'][service_name] = service_info
    
    # Create compatibility matrix
    services = list(schemas.keys())
    for i, service1 in enumerate(services):
        for j, service2 in enumerate(services):
            if i == j:
                continue
                
            key = f"{service1}_vs_{service2}"
            analysis['compatibility_matrix'][key] = {
                'compatible': True,  # Placeholder - would need actual comparison logic
                'breaking_changes': [],
                'common_endpoints': [],
                'common_models': []
            }
    
    # Generate summary
    total_endpoints = sum(len(s['endpoints']) for s in analysis['services'].values())
    total_models = sum(len(s['models']) for s in analysis['services'].values())
    
    analysis['summary'] = {
        'total_services': len(analysis['services']),
        'total_endpoints': total_endpoints,
        'total_models': total_models,
        'latest_versions': {name: info['version'] for name, info in analysis['services'].items()}
    }
    
    return analysis

def generate_markdown_report(analysis: Dict[str, Any]) -> str:
    """Generate a markdown report from the analysis."""
    
    report = f"""# API Version Compatibility Report

Generated: {analysis['generated_at']}

## Summary

- **Total Services**: {analysis['summary']['total_services']}
- **Total Endpoints**: {analysis['summary']['total_endpoints']}
- **Total Models**: {analysis['summary']['total_models']}

## Service Versions

"""
    
    for service_name, info in analysis['services'].items():
        report += f"""### {service_name.title()}

- **Version**: {info['version']}
- **Title**: {info['title']}
- **Endpoints**: {len(info['endpoints'])}
- **Models**: {len(info['models'])}
- **Generated**: {info['version_info'].get('generated_at', 'unknown')}
- **Last Commit**: {info['version_info'].get('git_info', {}).get('commit_hash', 'unknown')[:8]}

"""
    
    report += """## Compatibility Matrix

| Service | Version | Status | Breaking Changes |
|---------|---------|--------|------------------|
"""
    
    for service_name, info in analysis['services'].items():
        status = "✅ Stable" if info['compatibility']['breaking_changes'] == [] else "⚠️ Breaking Changes"
        breaking_changes = ", ".join(info['compatibility']['breaking_changes']) or "None"
        report += f"| {service_name.title()} | {info['version']} | {status} | {breaking_changes} |\n"
    
    report += """
## Endpoint Coverage

"""
    
    for service_name, info in analysis['services'].items():
        report += f"### {service_name.title()} ({len(info['endpoints'])} endpoints)\n\n"
        for endpoint in sorted(info['endpoints']):
            report += f"- `{endpoint}`\n"
        report += "\n"
    
    report += """## Model Coverage

"""
    
    for service_name, info in analysis['services'].items():
        report += f"### {service_name.title()} ({len(info['models'])} models)\n\n"
        for model in sorted(info['models']):
            report += f"- `{model}`\n"
        report += "\n"
    
    return report

def main():
    """Main function to generate version compatibility matrix."""
    print("🔍 Generating version compatibility matrix...")
    
    # Find all schema files
    schemas = {}
    for service_dir in project_root.glob('services/*/'):
        schema_path = service_dir / 'openapi' / 'schema.json'
        if schema_path.exists():
            service_name = service_dir.name
            schemas[service_name] = load_schema(schema_path)
    
    if not schemas:
        print("⚠️  No schema files found")
        return
    
    print(f"Found {len(schemas)} schemas")
    
    # Analyze schemas
    analysis = analyze_schema_changes(schemas)
    
    # Generate report
    report = generate_markdown_report(analysis)
    
    # Save report
    report_path = project_root / 'docs' / 'version-compatibility-report.md'
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"✅ Version compatibility report generated: {report_path}")
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"  - Services: {analysis['summary']['total_services']}")
    print(f"  - Endpoints: {analysis['summary']['total_endpoints']}")
    print(f"  - Models: {analysis['summary']['total_models']}")
    
    # Print service versions
    print(f"\n🏷️  Service Versions:")
    for service_name, info in analysis['services'].items():
        print(f"  - {service_name}: {info['version']}")

if __name__ == '__main__':
    main()
