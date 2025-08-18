#!/usr/bin/env python3
"""
Tests for internal backfill endpoints (service-to-service communication)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.office.app.main import app
from services.office.core.settings import get_settings
from services.office.models.backfill import BackfillRequest, ProviderEnum

client = TestClient(app)


@pytest.fixture(autouse=True)
def patch_settings():
    """Patch the _settings global variable to return test settings."""
    import services.office.core.settings as office_settings

    test_settings = office_settings.Settings(
        db_url_office="sqlite:///:memory:",
        api_frontend_office_key="test-frontend-office-key",
        api_chat_office_key="test-chat-office-key",
        api_meetings_office_key="test-meetings-office-key",
        api_backfill_office_key="test-backfill-office-key",
        api_office_user_key="test-office-user-key",
        pagination_secret_key="test-pagination-secret-key",
    )

    # Directly set the singleton instead of using monkeypatch
    office_settings._settings = test_settings
    yield
    office_settings._settings = None


class TestInternalBackfillEndpoints:
    """Test internal backfill endpoints with API key authentication"""

    def setup_method(self):
        """Set up test data"""
        self.settings = get_settings()
        self.valid_backfill_key = self.settings.api_backfill_office_key
        # Use unique user emails for each test to avoid conflicts
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        self.test_user_email = f"test_{unique_id}@example.com"
        self.valid_request = {
            "provider": "microsoft",
            "max_emails": 10,
            "batch_size": 5,
        }

    def test_start_internal_backfill_success(self):
        """Test successful internal backfill job start"""
        with patch("services.office.api.backfill.run_backfill_job") as mock_run:
            mock_run.return_value = None

            response = client.post(
                f"/internal/backfill/start?user_id={self.test_user_email}",
                json=self.valid_request,
                headers={"X-API-Key": self.valid_backfill_key},
            )

            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "started"
            assert "Internal backfill job started successfully" in data["message"]

    def test_start_internal_backfill_missing_user_id(self):
        """Test internal backfill start without user_id parameter"""
        response = client.post(
            "/internal/backfill/start",
            json=self.valid_request,
            headers={"X-API-Key": self.valid_backfill_key},
        )

        assert response.status_code == 422  # Validation error

    def test_start_internal_backfill_invalid_email_format(self):
        """Test internal backfill start with invalid email format"""
        response = client.post(
            "/internal/backfill/start?user_id=invalid-email",
            json=self.valid_request,
            headers={"X-API-Key": self.valid_backfill_key},
        )

        assert response.status_code == 400
        # Check the error message in the response
        response_data = response.json()
        assert "Invalid email format" in response_data.get("message", "")

    def test_start_internal_backfill_invalid_api_key(self):
        """Test internal backfill start with invalid API key"""
        response = client.post(
            f"/internal/backfill/start?user_id={self.test_user_email}",
            json=self.valid_request,
            headers={"X-API-Key": "invalid-key"},
        )

        assert response.status_code == 401

    def test_start_internal_backfill_missing_api_key(self):
        """Test internal backfill start without API key"""
        response = client.post(
            f"/internal/backfill/start?user_id={self.test_user_email}",
            json=self.valid_request,
        )

        assert response.status_code == 401

    def test_get_internal_backfill_status_success(self):
        """Test successful internal backfill status retrieval"""
        # First start a job
        with patch("services.office.api.backfill.run_backfill_job") as mock_run:
            mock_run.return_value = None

            start_response = client.post(
                f"/internal/backfill/start?user_id={self.test_user_email}",
                json=self.valid_request,
                headers={"X-API-Key": self.valid_backfill_key},
            )

            job_id = start_response.json()["job_id"]

            # Then get status
            status_response = client.get(
                f"/internal/backfill/status/{job_id}?user_id={self.test_user_email}",
                headers={"X-API-Key": self.valid_backfill_key},
            )

            assert status_response.status_code == 200
            data = status_response.json()
            assert data["job_id"] == job_id
            assert data["user_id"] == self.test_user_email

    def test_get_internal_backfill_status_job_not_found(self):
        """Test internal backfill status for non-existent job"""
        response = client.get(
            "/internal/backfill/status/nonexistent?user_id=test@example.com",
            headers={"X-API-Key": self.valid_backfill_key},
        )

        assert response.status_code == 404
        # Check the error message in the response
        response_data = response.json()
        assert "Backfill job not found" in response_data.get("message", "")

    def test_list_internal_backfill_jobs_success(self):
        """Test successful internal backfill job listing"""
        # First start a job
        with patch("services.office.api.backfill.run_backfill_job") as mock_run:
            mock_run.return_value = None

            client.post(
                f"/internal/backfill/start?user_id={self.test_user_email}",
                json=self.valid_request,
                headers={"X-API-Key": self.valid_backfill_key},
            )

            # Then list jobs
            list_response = client.get(
                f"/internal/backfill/status?user_id={self.test_user_email}",
                headers={"X-API-Key": self.valid_backfill_key},
            )

            assert list_response.status_code == 200
            data = list_response.json()
            assert isinstance(data, list)
            assert len(data) >= 1
            assert any(job["user_id"] == self.test_user_email for job in data)

    def test_cancel_internal_backfill_job_success(self):
        """Test successful internal backfill job cancellation"""
        # First start a job
        with patch("services.office.api.backfill.run_backfill_job") as mock_run:
            mock_run.return_value = None

            start_response = client.post(
                f"/internal/backfill/start?user_id={self.test_user_email}",
                json=self.valid_request,
                headers={"X-API-Key": self.valid_backfill_key},
            )

            job_id = start_response.json()["job_id"]

            # Then cancel it
            cancel_response = client.delete(
                f"/internal/backfill/{job_id}?user_id={self.test_user_email}",
                headers={"X-API-Key": self.valid_backfill_key},
            )

            assert cancel_response.status_code == 200
            assert "cancelled successfully" in cancel_response.json()["message"]

    def test_cancel_internal_backfill_job_not_found(self):
        """Test internal backfill cancellation for non-existent job"""
        response = client.delete(
            "/internal/backfill/nonexistent?user_id=test@example.com",
            headers={"X-API-Key": self.valid_backfill_key},
        )

        assert response.status_code == 404
        # Check the error message in the response
        response_data = response.json()
        assert "Backfill job not found" in response_data.get("message", "")

    def test_max_emails_parameter_respected(self):
        """Test that max_emails parameter is passed through correctly"""
        request_with_max = {"provider": "microsoft", "max_emails": 25, "batch_size": 10}

        with patch("services.office.api.backfill.run_backfill_job") as mock_run:
            mock_run.return_value = None

            response = client.post(
                f"/internal/backfill/start?user_id={self.test_user_email}",
                json=request_with_max,
                headers={"X-API-Key": self.valid_backfill_key},
            )

            assert response.status_code == 200

            # Verify the job was created with max_emails
            job_id = response.json()["job_id"]
            status_response = client.get(
                f"/internal/backfill/status/{job_id}?user_id={self.test_user_email}",
                headers={"X-API-Key": self.valid_backfill_key},
            )

            assert status_response.status_code == 200
            job_data = status_response.json()
            assert job_data["request"]["max_emails"] == 25
