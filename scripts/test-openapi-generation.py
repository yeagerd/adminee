#!/usr/bin/env python3
"""
Test OpenAPI schema generation for all Briefly services.

This script tests that each service can generate a valid OpenAPI schema.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add the services directory to the Python path
services_dir = Path(__file__).parent.parent / "services"
sys.path.insert(0, str(services_dir))

def test_chat_service_openapi() -> Dict[str, Any]:
    """Test chat service OpenAPI generation."""
    try:
        from services.chat.main import app
        schema = app.openapi()
        print("✅ Chat service: OpenAPI schema generated successfully")
        return {"service": "chat", "status": "success", "schema": schema}
    except Exception as e:
        print(f"❌ Chat service: Failed to generate OpenAPI schema - {e}")
        return {"service": "chat", "status": "error", "error": str(e)}

def test_meetings_service_openapi() -> Dict[str, Any]:
    """Test meetings service OpenAPI generation."""
    try:
        from services.meetings.main import app
        schema = app.openapi()
        print("✅ Meetings service: OpenAPI schema generated successfully")
        return {"service": "meetings", "status": "success", "schema": schema}
    except Exception as e:
        print(f"❌ Meetings service: Failed to generate OpenAPI schema - {e}")
        return {"service": "meetings", "status": "error", "error": str(e)}

def test_office_service_openapi() -> Dict[str, Any]:
    """Test office service OpenAPI generation."""
    try:
        from services.office.app.main import app
        schema = app.openapi()
        print("✅ Office service: OpenAPI schema generated successfully")
        return {"service": "office", "status": "success", "schema": schema}
    except Exception as e:
        print(f"❌ Office service: Failed to generate OpenAPI schema - {e}")
        return {"service": "office", "status": "error", "error": str(e)}

def test_user_service_openapi() -> Dict[str, Any]:
    """Test user service OpenAPI generation."""
    try:
        from services.user.main import app
        schema = app.openapi()
        print("✅ User service: OpenAPI schema generated successfully")
        return {"service": "user", "status": "success", "schema": schema}
    except Exception as e:
        print(f"❌ User service: Failed to generate OpenAPI schema - {e}")
        return {"service": "user", "status": "error", "error": str(e)}

def test_shipments_service_openapi() -> Dict[str, Any]:
    """Test shipments service OpenAPI generation."""
    try:
        from services.shipments.main import app
        schema = app.openapi()
        print("✅ Shipments service: OpenAPI schema generated successfully")
        return {"service": "shipments", "status": "success", "schema": schema}
    except Exception as e:
        print(f"❌ Shipments service: Failed to generate OpenAPI schema - {e}")
        return {"service": "shipments", "status": "error", "error": str(e)}

def test_email_sync_service_openapi() -> Dict[str, Any]:
    """Test email sync service OpenAPI generation."""
    try:
        from services.email_sync.main import app
        schema = app.openapi()
        print("✅ Email sync service: OpenAPI schema generated successfully")
        return {"service": "email_sync", "status": "success", "schema": schema}
    except Exception as e:
        print(f"❌ Email sync service: Failed to generate OpenAPI schema - {e}")
        return {"service": "email_sync", "status": "error", "error": str(e)}



def save_schemas_to_files(results: list) -> None:
    """Save successful OpenAPI schemas to JSON files."""
    output_dir = Path(__file__).parent.parent / "openapi-schemas"
    output_dir.mkdir(exist_ok=True)
    
    for result in results:
        if result["status"] == "success":
            service_name = result["service"]
            schema = result["schema"]
            
            # Save schema to file
            schema_file = output_dir / f"{service_name}-openapi.json"
            with open(schema_file, 'w') as f:
                json.dump(schema, f, indent=2)
            print(f"💾 Saved {service_name} schema to {schema_file}")
    
    print(f"\n📁 All schemas saved to: {output_dir}")

def main():
    """Test OpenAPI generation for all services."""
    print("🚀 Testing OpenAPI schema generation for all Briefly services...\n")
    
    # Test all services
    results = [
        test_chat_service_openapi(),
        test_meetings_service_openapi(),
        test_office_service_openapi(),
        test_user_service_openapi(),
        test_shipments_service_openapi(),
        test_email_sync_service_openapi(),

    ]
    
    # Summary
    print("\n" + "="*60)
    print("📊 OPENAPI GENERATION TEST RESULTS")
    print("="*60)
    
    successful = sum(1 for r in results if r["status"] == "success")
    total = len(results)
    
    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{status_icon} {result['service']}: {result['status']}")
    
    print(f"\n🎯 Success Rate: {successful}/{total} ({successful/total*100:.1f}%)")
    
    if successful == total:
        print("🎉 All services successfully generate OpenAPI schemas!")
        
        # Save schemas to files
        print("\n💾 Saving schemas to files...")
        save_schemas_to_files(results)
        
        return 0
    else:
        print("⚠️  Some services failed to generate OpenAPI schemas.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
