"""
Tests for common pagination components.

This module tests the base cursor pagination functionality, token manager,
query builder, and schemas.
"""

from common.pagination import (
    BaseCursorPagination,
    CursorData,
    CursorPaginationRequest,
    CursorPaginationResponse,
    PaginationConfig,
    TokenManager,
)
from common.pagination.base import CursorInfo
from common.pagination.query_builder import (
    PostgreSQLCursorQueryBuilder,
    SQLAlchemyCursorQueryBuilder,
)


class TestPaginationConfig:
    """Test pagination configuration."""

    def test_pagination_config_defaults(self):
        """Test pagination config with default values."""
        config = PaginationConfig(secret_key="test-secret")

        assert config.secret_key == "test-secret"
        assert config.token_expiry == 3600
        assert config.max_page_size == 100
        assert config.default_page_size == 20

    def test_pagination_config_custom_values(self):
        """Test pagination config with custom values."""
        config = PaginationConfig(
            secret_key="custom-secret",
            token_expiry=7200,
            max_page_size=50,
            default_page_size=10,
        )

        assert config.secret_key == "custom-secret"
        assert config.token_expiry == 7200
        assert config.max_page_size == 50
        assert config.default_page_size == 10


class TestTokenManager:
    """Test token manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.token_manager = TokenManager("test-secret-key", 3600)

    def test_encode_decode_token(self):
        """Test basic token encoding and decoding."""
        data = {"test": "value", "number": 123}

        token = self.token_manager.encode_token(data)
        decoded_data = self.token_manager.decode_token(token)

        assert decoded_data == data

    def test_validate_token(self):
        """Test token validation."""
        data = {"test": "value"}
        token = self.token_manager.encode_token(data)

        assert self.token_manager.validate_token(token) is True
        assert self.token_manager.validate_token("invalid-token") is False

    def test_token_expiration(self):
        """Test token expiration."""
        # Create token manager with short expiry
        short_expiry_manager = TokenManager("test-secret", 1)
        data = {"test": "value"}
        token = short_expiry_manager.encode_token(data)

        # Token should be valid initially
        assert short_expiry_manager.validate_token(token) is True

        # Wait for expiration
        import time

        time.sleep(2)

        # Token should be expired
        assert short_expiry_manager.validate_token(token) is False

    def test_get_token_info(self):
        """Test getting token information."""
        data = {"test": "value"}
        token = self.token_manager.encode_token(data)

        info = self.token_manager.get_token_info(token)

        assert info is not None
        assert "created_at" in info
        assert "expires_at" in info
        assert info["is_expired"] is False

    def test_rotate_secret_key(self):
        """Test secret key rotation."""
        data = {"test": "value"}
        token = self.token_manager.encode_token(data)

        # Token should be valid with old key
        assert self.token_manager.validate_token(token) is True

        # Rotate key
        self.token_manager.rotate_secret_key("new-secret-key")

        # Token should be invalid with new key
        assert self.token_manager.validate_token(token) is False


class TestCursorInfo:
    """Test cursor information structure."""

    def test_cursor_info_creation(self):
        """Test creating cursor info."""
        cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        assert cursor_info.last_id == "123"
        assert cursor_info.last_timestamp == "2023-01-01T00:00:00Z"
        assert cursor_info.filters == {"carrier": "fedex"}
        assert cursor_info.direction == "next"
        assert cursor_info.limit == 20


class TestBaseCursorPagination:
    """Test base cursor pagination functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = PaginationConfig(secret_key="test-secret")

        # Create a concrete implementation for testing
        class TestPagination(BaseCursorPagination):
            def build_query_filters(self, cursor_info):
                return {"test": "filter"}

            def get_ordering_clause(self, direction="next"):
                return "id ASC" if direction == "next" else "id DESC"

        self.pagination = TestPagination(self.config)

    def test_encode_decode_cursor(self):
        """Test cursor encoding and decoding."""
        cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        token = self.pagination.encode_cursor(cursor_info)
        decoded_info = self.pagination.decode_cursor(token)

        assert decoded_info is not None
        assert decoded_info.last_id == cursor_info.last_id
        assert decoded_info.last_timestamp == cursor_info.last_timestamp
        assert decoded_info.filters == cursor_info.filters

    def test_validate_cursor(self):
        """Test cursor validation."""
        cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        token = self.pagination.encode_cursor(cursor_info)

        assert self.pagination.validate_cursor(token) is True
        assert self.pagination.validate_cursor("invalid-token") is False

    def test_sanitize_limit(self):
        """Test limit sanitization."""
        # Test default limit
        assert self.pagination.sanitize_limit(None) == 20

        # Test valid limit
        assert self.pagination.sanitize_limit(50) == 50

        # Test limit below minimum
        assert self.pagination.sanitize_limit(0) == 1

        # Test limit above maximum
        assert self.pagination.sanitize_limit(200) == 100

    def test_create_cursor_info(self):
        """Test creating cursor info."""
        cursor_info = self.pagination.create_cursor_info(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=30,
        )

        assert cursor_info.last_id == "123"
        assert cursor_info.last_timestamp == "2023-01-01T00:00:00Z"
        assert cursor_info.filters == {"carrier": "fedex"}
        assert cursor_info.direction == "next"
        assert cursor_info.limit == 30

    def test_create_pagination_response(self):
        """Test creating pagination response."""
        items = [{"id": "1"}, {"id": "2"}]

        response = self.pagination.create_pagination_response(
            items=items, has_next=True, has_prev=False
        )

        assert response["items"] == items
        assert response["has_next"] is True
        assert response["has_prev"] is False
        assert response["limit"] == 20


class TestSQLAlchemyCursorQueryBuilder:
    """Test SQLAlchemy cursor query builder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.query_builder = SQLAlchemyCursorQueryBuilder()
        self.cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

    def test_build_cursor_filter_next(self):
        """Test building cursor filter for next page."""
        filter_condition, params = self.query_builder.build_cursor_filter(
            self.cursor_info, "id", "updated_at"
        )

        assert "updated_at > :last_timestamp" in filter_condition
        assert "updated_at = :last_timestamp AND id > :last_id" in filter_condition
        assert params["last_timestamp"] == "2023-01-01T00:00:00Z"
        assert params["last_id"] == "123"

    def test_build_cursor_filter_prev(self):
        """Test building cursor filter for previous page."""
        prev_cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={},
            direction="prev",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        filter_condition, params = self.query_builder.build_cursor_filter(
            prev_cursor_info, "id", "updated_at"
        )

        assert "updated_at < :last_timestamp" in filter_condition
        assert "updated_at = :last_timestamp AND id < :last_id" in filter_condition

    def test_build_ordering_clause(self):
        """Test building ordering clause."""
        next_ordering = self.query_builder.build_ordering_clause(
            "id", "updated_at", "next"
        )
        prev_ordering = self.query_builder.build_ordering_clause(
            "id", "updated_at", "prev"
        )

        assert next_ordering == "updated_at ASC, id ASC"
        assert prev_ordering == "updated_at DESC, id DESC"

    def test_build_limit_clause(self):
        """Test building limit clause."""
        limit_clause, params = self.query_builder.build_limit_clause(20)

        assert limit_clause == "LIMIT :limit"
        assert params["limit"] == 20

    def test_build_base_query(self):
        """Test building complete base query."""
        query, params = self.query_builder.build_base_query(
            "packages", self.cursor_info, {"carrier": "fedex"}, "id", "updated_at"
        )

        assert "SELECT * FROM packages" in query
        assert "WHERE" in query
        assert "ORDER BY" in query
        assert "LIMIT" in query
        assert "filter_carrier" in params


class TestPostgreSQLCursorQueryBuilder:
    """Test PostgreSQL-specific cursor query builder."""

    def setup_method(self):
        """Set up test fixtures."""
        self.query_builder = PostgreSQLCursorQueryBuilder()
        self.cursor_info = CursorInfo(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

    def test_build_cursor_filter_postgresql(self):
        """Test PostgreSQL-specific cursor filter."""
        filter_condition, params = self.query_builder.build_cursor_filter(
            self.cursor_info, "id", "updated_at"
        )

        # Should use PostgreSQL row comparison syntax
        assert "(updated_at, id) > (:last_timestamp, :last_id)" in filter_condition
        assert params["last_timestamp"] == "2023-01-01T00:00:00Z"
        assert params["last_id"] == "123"


class TestPaginationSchemas:
    """Test pagination schemas."""

    def test_cursor_pagination_request(self):
        """Test cursor pagination request schema."""
        request = CursorPaginationRequest(
            cursor="test-cursor", limit=50, direction="next"
        )

        assert request.cursor == "test-cursor"
        assert request.limit == 50
        assert request.direction == "next"

    def test_cursor_pagination_response(self):
        """Test cursor pagination response schema."""
        response = CursorPaginationResponse(
            items=[{"id": "1"}, {"id": "2"}],
            next_cursor="next-cursor",
            prev_cursor=None,
            has_next=True,
            has_prev=False,
            limit=20,
        )

        assert len(response.items) == 2
        assert response.next_cursor == "next-cursor"
        assert response.prev_cursor is None
        assert response.has_next is True
        assert response.has_prev is False
        assert response.limit == 20

    def test_cursor_data(self):
        """Test cursor data schema."""
        cursor_data = CursorData(
            last_id="123",
            last_timestamp="2023-01-01T00:00:00Z",
            filters={"carrier": "fedex"},
            direction="next",
            limit=20,
            created_at="2023-01-01T00:00:00Z",
        )

        assert cursor_data.last_id == "123"
        assert cursor_data.last_timestamp == "2023-01-01T00:00:00Z"
        assert cursor_data.filters == {"carrier": "fedex"}
        assert cursor_data.direction == "next"
        assert cursor_data.limit == 20
