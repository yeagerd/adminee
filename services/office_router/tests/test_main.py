#!/usr/bin/env python3
"""
Tests for the office router service main endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

# Mock environment variables before importing the app
os.environ["ENVIRONMENT"] = "test"
os.environ["API_FRONTEND_OFFICE_ROUTER_KEY"] = "test-frontend-key"
os.environ["API_OFFICE_ROUTER_USER_KEY"] = "test-user-key"
os.environ["API_OFFICE_ROUTER_OFFICE_KEY"] = "test-office-key"

from services.office_router.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch("services.office_router.main.settings") as mock:
        mock.api_frontend_office_router_key = "test-frontend-key"
        mock.api_office_router_user_key = "test-user-key"
        mock.api_office_router_office_key = "test-office-key"
        yield mock


@pytest.fixture
def mock_router_and_pubsub():
    """Mock router and pubsub consumer for testing"""
    with patch("services.office_router.main.router") as mock_router, \
         patch("services.office_router.main.pubsub_consumer") as mock_pubsub:
        
        # Mock router
        mock_router.get_downstream_services.return_value = {"test": "service"}
        
        # Mock pubsub consumer
        mock_pubsub.get_running_status.return_value = True
        mock_pubsub.get_subscription_status.return_value = {"test": "subscription"}
        
        yield mock_router, mock_pubsub


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "office-router"
    assert data["version"] == "1.0.0"


def test_service_status_not_ready(client):
    """Test service status when not ready"""
    response = client.get("/status")
    assert response.status_code == 503
    data = response.json()
    assert "Service not ready" in data["message"]


def test_service_status_ready(client, mock_router_and_pubsub):
    """Test service status when ready"""
    mock_router, mock_pubsub = mock_router_and_pubsub
    
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["router"]["status"] == "running"
    assert data["pubsub"]["status"] == "running"


def test_route_email_missing_api_key(client):
    """Test route email without API key"""
    response = client.post("/route/email", json={"test": "data"})
    assert response.status_code == 422  # Validation error for missing header


def test_route_email_invalid_api_key(client, mock_settings):
    """Test route email with invalid API key"""
    response = client.post(
        "/route/email",
        json={"test": "data"},
        headers={"X-API-Key": "invalid-key"}
    )
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["message"]


def test_route_calendar_missing_api_key(client):
    """Test route calendar without API key"""
    response = client.post("/route/calendar", json={"test": "data"})
    assert response.status_code == 422  # Validation error for missing header


def test_route_contact_missing_api_key(client):
    """Test route contact without API key"""
    response = client.post("/route/contact", json={"test": "data"})
    assert response.status_code == 422  # Validation error for missing header
