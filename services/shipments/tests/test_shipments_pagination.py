"""
Tests for shipments pagination implementation.

This module tests the shipments-specific cursor pagination functionality.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from services.shipments.utils.pagination import ShipmentsCursorPagination
from services.shipments.schemas.pagination import (
    PackageListRequest,
    PackageListResponse,
    PackageSearchRequest,
    PackageSearchResponse,
    CursorValidationError,
    PaginationError,
)
from common.pagination import PaginationConfig
from common.pagination.base import CursorInfo


class TestShipmentsCursorPagination:
    """Test shipments-specific cursor pagination."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = PaginationConfig(
            secret_key="test-secret-key",
            token_expiry=3600,
            max_page_size=100,
            default_page_size=20
        )
        self.pagination = ShipmentsCursorPagination(self.config)
    
    def test_build_query_filters_next(self):
        """Test building query filters for next page."""
        cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex", "status": "delivered"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z"
        )
        
        filters = self.pagination.build_query_filters(cursor_info)
        
        assert "cursor_filter" in filters
        assert "cursor_params" in filters
        assert "carrier" in filters
        assert "status" in filters
        assert filters["carrier"] == "fedex"
        assert filters["status"] == "delivered"
    
    def test_build_query_filters_prev(self):
        """Test building query filters for previous page."""
        cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "ups"},
            direction="prev",
            limit=20,
            created_at="2023-01-01T00:00:00Z"
        )
        
        filters = self.pagination.build_query_filters(cursor_info)
        
        assert "cursor_filter" in filters
        assert "cursor_params" in filters
        assert "carrier" in filters
        assert filters["carrier"] == "ups"
    
    def test_get_ordering_clause(self):
        """Test getting ordering clause."""
        next_ordering = self.pagination.get_ordering_clause("next")
        prev_ordering = self.pagination.get_ordering_clause("prev")
        
        assert next_ordering == "updated_at ASC, id ASC"
        assert prev_ordering == "updated_at DESC, id DESC"
    
    def test_create_shipments_cursor_info(self):
        """Test creating shipments-specific cursor info."""
        cursor_info = self.pagination.create_shipments_cursor_info(
            last_id="123",
            last_updated="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=30
        )
        
        assert cursor_info.last_id == "123"
        assert cursor_info.last_timestamp == "2023-01-01T00:00:00Z"
        assert cursor_info.filters == {"carrier": "fedex"}
        assert cursor_info.direction == "next"
        assert cursor_info.limit == 30
    
    def test_build_shipments_query(self):
        """Test building shipments query."""
        cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z"
        )
        
        query, params = self.pagination.build_shipments_query(
            cursor_info=cursor_info,
            additional_filters={"status": "delivered"}
        )
        
        assert "SELECT * FROM packages" in query
        assert "WHERE" in query
        assert "ORDER BY" in query
        assert "LIMIT" in query
    
    def test_create_shipments_pagination_response(self):
        """Test creating shipments pagination response."""
        packages = [
            {"id": "1", "tracking_number": "123456789"},
            {"id": "2", "tracking_number": "987654321"}
        ]
        
        cursor_info = CursorInfo(
            last_id="2",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z"
        )
        
        response = self.pagination.create_shipments_pagination_response(
            packages=packages,
            cursor_info=cursor_info,
            has_next=True,
            has_prev=False
        )
        
        assert "packages" in response
        assert response["packages"] == packages
        assert response["has_next"] is True
        assert response["has_prev"] is False
        assert response["limit"] == 20
        assert "next_cursor" in response
    
    def test_validate_shipments_filters(self):
        """Test validating shipments filters."""
        raw_filters = {
            "carrier": "  fedex  ",
            "status": "delivered",
            "tracking_number": "  123456789  ",
            "user_id": "user123",
            "invalid_filter": "should_be_ignored"
        }
        
        validated_filters = self.pagination.validate_shipments_filters(raw_filters)
        
        assert "carrier" in validated_filters
        assert "status" in validated_filters
        assert "tracking_number" in validated_filters
        assert "user_id" in validated_filters
        assert "invalid_filter" not in validated_filters
        
        # Check that whitespace was stripped
        assert validated_filters["carrier"] == "fedex"
        assert validated_filters["tracking_number"] == "123456789"
    
    def test_validate_shipments_filters_empty_values(self):
        """Test validating shipments filters with empty values."""
        raw_filters = {
            "carrier": "",
            "status": None,
            "tracking_number": "   ",
            "user_id": ""
        }
        
        validated_filters = self.pagination.validate_shipments_filters(raw_filters)
        
        # Empty values should be filtered out
        assert len(validated_filters) == 0


class TestPackageListRequest:
    """Test package list request schema."""
    
    def test_package_list_request_defaults(self):
        """Test package list request with default values."""
        request = PackageListRequest()
        
        assert request.cursor is None
        assert request.limit is None
        assert request.direction == "next"
        assert request.carrier is None
        assert request.status is None
        assert request.user_id is None
    
    def test_package_list_request_with_values(self):
        """Test package list request with values."""
        request = PackageListRequest(
            cursor="test-cursor",
            limit=50,
            direction="prev",
            carrier="fedex",
            status="delivered",
            user_id="user123"
        )
        
        assert request.cursor == "test-cursor"
        assert request.limit == 50
        assert request.direction == "prev"
        assert request.carrier == "fedex"
        assert request.status == "delivered"
        assert request.user_id == "user123"
    
    def test_package_list_request_invalid_direction(self):
        """Test package list request with invalid direction."""
        with pytest.raises(ValueError):
            PackageListRequest(direction="invalid")


class TestPackageListResponse:
    """Test package list response schema."""
    
    def test_package_list_response(self):
        """Test package list response."""
        packages = [
            {"id": "1", "tracking_number": "123456789"},
            {"id": "2", "tracking_number": "987654321"}
        ]
        
        response = PackageListResponse(
            packages=packages,
            next_cursor="next-cursor",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            limit=20
        )
        
        assert response.packages == packages
        assert response.next_cursor == "next-cursor"
        assert response.prev_cursor is None
        assert response.has_next is True
        assert response.has_prev is False
        assert response.limit == 20


class TestPackageSearchRequest:
    """Test package search request schema."""
    
    def test_package_search_request(self):
        """Test package search request."""
        request = PackageSearchRequest(
            cursor="test-cursor",
            limit=30,
            direction="next",
            tracking_number="123456789",
            carrier="fedex",
            status="delivered",
            user_id="user123",
            query="test search"
        )
        
        assert request.cursor == "test-cursor"
        assert request.limit == 30
        assert request.direction == "next"
        assert request.tracking_number == "123456789"
        assert request.carrier == "fedex"
        assert request.status == "delivered"
        assert request.user_id == "user123"
        assert request.query == "test search"


class TestPackageSearchResponse:
    """Test package search response schema."""
    
    def test_package_search_response(self):
        """Test package search response."""
        packages = [
            {"id": "1", "tracking_number": "123456789"},
            {"id": "2", "tracking_number": "987654321"}
        ]
        
        response = PackageSearchResponse(
            packages=packages,
            next_cursor="next-cursor",
            prev_cursor="prev-cursor",
            has_next=True,
            has_prev=True,
            limit=20,
            search_query="test search"
        )
        
        assert response.packages == packages
        assert response.next_cursor == "next-cursor"
        assert response.prev_cursor == "prev-cursor"
        assert response.has_next is True
        assert response.has_prev is True
        assert response.limit == 20
        assert response.search_query == "test search"


class TestCursorValidationError:
    """Test cursor validation error schema."""
    
    def test_cursor_validation_error(self):
        """Test cursor validation error."""
        error = CursorValidationError(
            error="Invalid cursor token",
            cursor_token="invalid-token",
            reason="Token expired"
        )
        
        assert error.error == "Invalid cursor token"
        assert error.error_code == "INVALID_CURSOR"
        assert error.cursor_token == "invalid-token"
        assert error.reason == "Token expired"


class TestPaginationError:
    """Test pagination error schema."""
    
    def test_pagination_error(self):
        """Test pagination error."""
        error = PaginationError(
            error="Pagination failed",
            error_code="PAGINATION_ERROR",
            details={"reason": "Invalid parameters"}
        )
        
        assert error.error == "Pagination failed"
        assert error.error_code == "PAGINATION_ERROR"
        assert error.details == {"reason": "Invalid parameters"}


class TestShipmentsPaginationIntegration:
    """Integration tests for shipments pagination."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = PaginationConfig(
            secret_key="test-secret-key",
            token_expiry=3600,
            max_page_size=100,
            default_page_size=20
        )
        self.pagination = ShipmentsCursorPagination(self.config)
    
    def test_full_pagination_flow(self):
        """Test complete pagination flow."""
        # Create initial cursor info
        cursor_info = self.pagination.create_shipments_cursor_info(
            last_id="123",
            last_updated="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=20
        )
        
        # Encode cursor
        token = self.pagination.encode_cursor(cursor_info)
        
        # Decode cursor
        decoded_info = self.pagination.decode_cursor(token)
        
        # Verify cursor info
        assert decoded_info is not None
        assert decoded_info.last_id == "123"
        assert decoded_info.last_timestamp == "2023-01-01T00:00:00Z"
        assert decoded_info.filters == {"carrier": "fedex"}
        assert decoded_info.direction == "next"
        assert decoded_info.limit == 20
        
        # Build query filters
        filters = self.pagination.build_query_filters(decoded_info)
        
        # Verify filters
        assert "cursor_filter" in filters
        assert "cursor_params" in filters
        assert "carrier" in filters
        assert filters["carrier"] == "fedex"
        
        # Create pagination response
        packages = [{"id": "1"}, {"id": "2"}]
        response = self.pagination.create_shipments_pagination_response(
            packages=packages,
            cursor_info=decoded_info,
            has_next=True,
            has_prev=False
        )
        
        # Verify response
        assert "packages" in response
        assert response["packages"] == packages
        assert response["has_next"] is True
        assert response["has_prev"] is False
        assert "next_cursor" in response
    
    def test_pagination_with_various_filters(self):
        """Test pagination with different filter combinations."""
        filter_combinations = [
            {"carrier": "fedex"},
            {"status": "delivered"},
            {"carrier": "ups", "status": "in_transit"},
            {"tracking_number": "123456789"},
            {"user_id": "user123"},
            {}  # No filters
        ]
        
        for filters in filter_combinations:
            cursor_info = self.pagination.create_shipments_cursor_info(
                last_id="123",
                last_updated="2023-01-01T00:00:00Z",
                filters=filters,
                direction="next",
                limit=20
            )
            
            # Validate filters
            validated_filters = self.pagination.validate_shipments_filters(filters)
            
            # Build query filters
            query_filters = self.pagination.build_query_filters(cursor_info)
            
            # Verify that filters are properly handled
            for key, value in validated_filters.items():
                assert key in query_filters
                assert query_filters[key] == value
    
    def test_bidirectional_pagination(self):
        """Test bidirectional pagination."""
        # Test next page
        next_cursor_info = self.pagination.create_shipments_cursor_info(
            last_id="123",
            last_updated="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=20
        )
        
        next_filters = self.pagination.build_query_filters(next_cursor_info)
        next_ordering = self.pagination.get_ordering_clause("next")
        
        # Test previous page
        prev_cursor_info = self.pagination.create_shipments_cursor_info(
            last_id="123",
            last_updated="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="prev",
            limit=20
        )
        
        prev_filters = self.pagination.build_query_filters(prev_cursor_info)
        prev_ordering = self.pagination.get_ordering_clause("prev")
        
        # Verify different behavior for next vs prev
        assert next_ordering != prev_ordering
        assert "ASC" in next_ordering
        assert "DESC" in prev_ordering 