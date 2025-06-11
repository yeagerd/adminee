#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

# Import the app and dependencies
from main import app
from auth.clerk import get_current_user, verify_user_ownership
from schemas.integration import IntegrationStatsResponse

def test_stats_endpoint():
    """Debug the stats endpoint to see what's causing 422 error."""
    
    # Create test client
    client = TestClient(app)
    
    # Mock authentication
    async def mock_get_current_user():
        return "user_123"
    
    async def mock_verify_user_ownership(current_user_id: str, resource_user_id: str):
        return None  # No exception means authorized
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # Mock the service response
    mock_response = IntegrationStatsResponse(
        total_integrations=2,
        active_integrations=1,
        failed_integrations=1,
        pending_integrations=0,
        by_provider={"google": 1, "microsoft": 1},
        by_status={"active": 1, "error": 1, "inactive": 0, "pending": 0},
        recent_errors=[],
        sync_stats={}
    )
    
    try:
        with patch('services.integration_service.integration_service.get_integration_statistics', return_value=mock_response):
            with patch('auth.clerk.verify_user_ownership', side_effect=mock_verify_user_ownership):
                response = client.get(
                    "/users/user_123/integrations/stats",
                    headers={"Authorization": "Bearer valid-token"}
                )
                
                print(f"Status Code: {response.status_code}")
                print(f"Response Text: {response.text}")
                print(f"Response Headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    try:
                        error_detail = response.json()
                        print(f"Error Detail: {error_detail}")
                    except:
                        print("Could not parse error response as JSON")
                        
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        app.dependency_overrides.clear()

if __name__ == "__main__":
    test_stats_endpoint() 