"""
Unit tests for the calendar integration service in the Meetings Service.

Tests the integration with the Office Service including:
- API client creation
- Availability requests
- Error handling
- Response processing
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from services.meetings.tests.test_base import BaseMeetingsTest
from services.meetings.services.calendar_integration import get_user_availability


class TestCalendarIntegration(BaseMeetingsTest):
    """Test suite for the calendar integration service."""

    def setup_method(self, method):
        """Set up test environment."""
        super().setup_method(method)
        
        # Test data
        self.test_user_id = "test-user-123"
        self.start_date = datetime.now(timezone.utc)
        self.end_date = self.start_date + timedelta(days=30)
        self.duration_minutes = 30
        
        # Mock office service response
        self.mock_office_response = {
            "data": {
                "available_slots": [
                    {
                        "start": "2025-08-15T09:00:00Z",
                        "end": "2025-08-15T09:30:00Z",
                        "duration_minutes": 30
                    },
                    {
                        "start": "2025-08-15T14:00:00Z",
                        "end": "2025-08-15T14:30:00Z",
                        "duration_minutes": 30
                    }
                ],
                "total_slots": 2,
                "providers_used": ["microsoft"],
                "request_metadata": {}
            }
        }
        
        # Sample date ranges for testing
        self.sample_date_ranges = [
            (datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(days=1)),
            (datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(days=7)),
            (datetime.now(timezone.utc), datetime.now(timezone.utc) + timedelta(days=30)),
        ]
        
        # Sample durations for testing
        self.sample_durations = [15, 30, 60, 120]

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_success(self, mock_client_class):
        """Test successful availability request to office service."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_office_response
        mock_client.get.return_value = mock_response
        
        # Call the service
        result = await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Verify result
        assert result == self.mock_office_response
        
        # Verify the client was called correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        
        # Check URL
        url = call_args[0][0]
        assert "/v1/calendar/availability" in url
        
        # Check query parameters
        params = call_args[1]["params"]
        assert params["start"] == self.start_date.isoformat()
        assert params["end"] == self.end_date.isoformat()
        assert params["duration"] == self.duration_minutes

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_with_headers(self, mock_client_class):
        """Test availability request includes proper authentication headers."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_office_response
        mock_client.get.return_value = mock_response
        
        # Call the service
        await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Verify headers were set correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        
        # Check headers
        headers = call_args[1]["headers"]
        assert "X-API-Key" in headers
        assert headers["X-API-Key"] == "test-meetings-office-key"

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_http_error(self, mock_client_class):
        """Test handling of HTTP errors from office service."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.get.return_value = mock_response
        
        # Call the service - should handle error gracefully
        result = await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Should return empty response on error
        assert result == {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {}
            }
        }

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_network_error(self, mock_client_class):
        """Test handling of network errors."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock network error
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        
        # Call the service - should handle error gracefully
        result = await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Should return empty response on error
        assert result == {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {}
            }
        }

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_timeout_error(self, mock_client_class):
        """Test handling of timeout errors."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock timeout error
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
        
        # Call the service - should handle error gracefully
        result = await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Should return empty response on error
        assert result == {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {}
            }
        }

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_unauthorized(self, mock_client_class):
        """Test handling of unauthorized responses."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock unauthorized response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_client.get.return_value = mock_response
        
        # Call the service - should handle error gracefully
        result = await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Should return empty response on error
        assert result == {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {}
            }
        }

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_bad_request(self, mock_client_class):
        """Test handling of bad request responses."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock bad request response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_client.get.return_value = mock_response
        
        # Call the service - should handle error gracefully
        result = await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Should return empty response on error
        assert result == {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {}
            }
        }

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_malformed_response(self, mock_client_class):
        """Test handling of malformed responses from office service."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful response but with malformed JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = mock_response
        
        # Call the service - should handle error gracefully
        result = await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Should return empty response on error
        assert result == {
            "data": {
                "available_slots": [],
                "total_slots": 0,
                "providers_used": [],
                "request_metadata": {}
            }
        }

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_different_durations(self, mock_client_class):
        """Test availability requests with different meeting durations."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_office_response
        mock_client.get.return_value = mock_response
        
        # Test different durations
        for duration in self.sample_durations:
            await get_user_availability(
                user_id=self.test_user_id,
                start=self.start_date,
                end=self.end_date,
                duration=duration
            )
            
            # Verify the duration parameter was passed correctly
            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert params["duration"] == duration

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_date_range_handling(self, mock_client_class):
        """Test proper handling of date ranges."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_office_response
        mock_client.get.return_value = mock_response
        
        # Test with different date ranges
        for start, end in self.sample_date_ranges:
            await get_user_availability(
                user_id=self.test_user_id,
                start=start,
                end=end,
                duration=self.duration_minutes
            )
            
            # Verify the date parameters were passed correctly
            call_args = mock_client.get.call_args
            params = call_args[1]["params"]
            assert params["start"] == start.isoformat()
            assert params["end"] == end.isoformat()

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_timezone_handling(self, mock_client_class):
        """Test proper timezone handling in requests."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_office_response
        mock_client.get.return_value = mock_response
        
        # Test with timezone-aware datetimes
        utc_tz = timezone.utc
        start_utc = datetime.now(utc_tz)
        end_utc = start_utc + timedelta(days=1)
        
        await get_user_availability(
            user_id=self.test_user_id,
            start=start_utc,
            end=end_utc,
            duration=self.duration_minutes
        )
        
        # Verify the timezone-aware datetimes are handled correctly
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        
        # Should be ISO format with timezone info
        assert "Z" in params["start"] or "+" in params["start"]
        assert "Z" in params["end"] or "+" in params["end"]

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_client_cleanup(self, mock_client_class):
        """Test that the HTTP client is properly cleaned up."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.mock_office_response
        mock_client.get.return_value = mock_response
        
        # Call the service
        await get_user_availability(
            user_id=self.test_user_id,
            start=self.start_date,
            end=self.end_date,
            duration=self.duration_minutes
        )
        
        # Verify the client context manager was used
        mock_client_class.assert_called_once()
        mock_client_class.return_value.__aenter__.assert_called_once()
        mock_client_class.return_value.__aexit__.assert_called_once()

    @patch('services.meetings.services.calendar_integration.httpx.AsyncClient')
    async def test_get_user_availability_retry_logic(self, mock_client_class):
        """Test that the service handles transient failures gracefully."""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock first call fails, second call succeeds
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        
        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = self.mock_office_response
        
        mock_client.get.side_effect = [mock_response_fail, mock_response_success]
        
        # Call the service multiple times
        for i in range(2):
            result = await get_user_availability(
                user_id=self.test_user_id,
                start=self.start_date,
                end=self.end_date,
                duration=self.duration_minutes
            )
            
            if i == 0:
                # First call should fail and return empty response
                assert result == {
                    "data": {
                        "available_slots": [],
                        "total_slots": 0,
                        "providers_used": [],
                        "request_metadata": {}
                    }
                }
            else:
                # Second call should succeed
                assert result == self.mock_office_response
