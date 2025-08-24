"""
Tests for idempotency functionality.
"""

import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from services.common.events.base_events import EventMetadata
from services.common.events.calendar_events import CalendarEvent, CalendarEventData
from services.common.events.contact_events import ContactData, ContactEvent
from services.common.events.email_events import EmailData, EmailEvent
from services.common.idempotency.idempotency_keys import (
    IdempotencyKeyGenerator,
    IdempotencyKeyValidator,
    IdempotencyStrategy,
)
from services.common.idempotency.idempotency_service import IdempotencyService
from services.common.idempotency.redis_reference import RedisReferencePattern


class TestIdempotencyKeyGenerator:
    """Test idempotency key generation."""

    @pytest.fixture
    def sample_email_event(self):
        """Create a sample email event."""
        return EmailEvent(
            metadata=EventMetadata(
                event_id="event123",
                source_service="test-service",
                source_version="1.0.0",
            ),
            user_id="user123",
            email=EmailData(
                id="email123",
                thread_id="thread123",
                subject="Test",
                body="Test body",
                from_address="sender@example.com",
                to_addresses=[],
                cc_addresses=[],
                received_date=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                provider="gmail",
                provider_message_id="msg123",
            ),
            operation="create",
            batch_id="batch123",
            last_updated=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            sync_timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            provider="gmail",
            sync_type="backfill",
        )

    @pytest.fixture
    def sample_calendar_event(self):
        """Create a sample calendar event."""
        return CalendarEvent(
            metadata=EventMetadata(
                event_id="event456",
                source_service="test-service",
                source_version="1.0.0",
            ),
            user_id="user123",
            event=CalendarEventData(
                id="cal123",
                title="Test Meeting",
                start_time=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
                organizer="organizer@example.com",
                attendees=[],
                provider="google",
                provider_event_id="event123",
                calendar_id="cal1",
            ),
            operation="create",
            batch_id="batch123",
            last_updated=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            sync_timestamp=datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            provider="google",
            calendar_id="cal1",
        )

    @pytest.fixture
    def sample_contact_event(self):
        """Create a sample contact event."""
        return ContactEvent(
            metadata=EventMetadata(
                event_id="event789",
                source_service="test-service",
                source_version="1.0.0",
            ),
            user_id="user123",
            contact=ContactData(
                id="contact123",
                email_address="contact@example.com",
                display_name="John Doe",
                first_name="John",
                last_name="Doe",
                provider="google",
                provider_contact_id="contact123",
            ),
            operation="create",
            batch_id="batch123",
            last_updated=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            sync_timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            provider="google",
        )

    def test_generate_email_key(self, sample_email_event):
        """Test email key generation."""
        key = IdempotencyKeyGenerator.generate_email_key(sample_email_event)
        assert len(key) == 32
        assert key.isalnum()

    def test_generate_calendar_key(self, sample_calendar_event):
        """Test calendar key generation."""
        key = IdempotencyKeyGenerator.generate_calendar_key(sample_calendar_event)
        assert len(key) == 32
        assert key.isalnum()

    def test_generate_generic_key(self):
        """Test generic key generation."""
        key = IdempotencyKeyGenerator.generate_generic_key(
            "test", "doc123", "user123", "gmail", "create"
        )
        assert len(key) == 32
        assert key.isalnum()

    def test_generate_batch_key(self):
        """Test batch key generation."""
        key = IdempotencyKeyGenerator.generate_batch_key("batch123", "user123")
        assert len(key) == 32
        assert key.isalnum()

    def test_key_hashing_consistency(self):
        """Test that the same input always produces the same hash."""
        key1 = IdempotencyKeyGenerator.generate_generic_key(
            "test", "doc123", "user123", "gmail", "create"
        )
        key2 = IdempotencyKeyGenerator.generate_generic_key(
            "test", "doc123", "user123", "gmail", "create"
        )
        assert key1 == key2

    def test_parse_key_components(self):
        """Test parsing key components."""
        components = IdempotencyKeyGenerator.parse_key_components("a" * 32)
        assert components["key"] == "a" * 32
        assert components["length"] == 32
        assert components["is_hex"] is True


class TestIdempotencyStrategy:
    """Test idempotency strategy classification."""

    def test_immutable_operations(self):
        """Test immutable operation classification."""
        assert IdempotencyStrategy.is_immutable_operation("email", "create") is True
        assert IdempotencyStrategy.is_immutable_operation("calendar", "create") is True
        assert IdempotencyStrategy.is_immutable_operation("email", "update") is not True

    def test_mutable_operations(self):
        """Test mutable operation classification."""
        assert IdempotencyStrategy.is_mutable_operation("email", "update") is True
        assert IdempotencyStrategy.is_mutable_operation("email", "delete") is True
        assert IdempotencyStrategy.is_mutable_operation("email", "create") is not True

    def test_batch_operations(self):
        """Test batch operation classification."""
        assert IdempotencyStrategy.is_batch_operation("email", "batch_create") is True
        assert (
            IdempotencyStrategy.is_batch_operation("calendar", "batch_update") is True
        )
        assert IdempotencyStrategy.is_batch_operation("email", "create") is not True

    def test_get_key_strategy(self):
        """Test getting key strategy for operations."""
        assert IdempotencyStrategy.get_key_strategy("email", "create") == "immutable"
        assert IdempotencyStrategy.get_key_strategy("email", "update") == "mutable"
        assert IdempotencyStrategy.get_key_strategy("email", "batch_create") == "batch"

    def test_get_key_components(self):
        """Test getting key components for different strategies."""
        components = IdempotencyStrategy.get_key_components("email", "create")
        assert components["include_provider_id"] is True
        assert components["include_message_id"] is True
        assert components["include_user_id"] is True


class TestIdempotencyKeyValidator:
    """Test idempotency key validation."""

    def test_validate_key_format(self):
        """Test key format validation."""
        # Valid key (32 hex characters)
        valid_key = "a" * 32
        assert IdempotencyKeyValidator.validate_key_format(valid_key) is True

        # Invalid keys
        assert IdempotencyKeyValidator.validate_key_format("") is False
        assert IdempotencyKeyValidator.validate_key_format("short") is False
        assert IdempotencyKeyValidator.validate_key_format("a" * 33) is False

    def test_validate_key_uniqueness(self):
        """Test key uniqueness validation."""
        existing_keys = {"key1", "key2", "key3"}

        # New key should be unique
        assert (
            IdempotencyKeyValidator.validate_key_uniqueness(existing_keys, "new_key")
            is True
        )

        # Existing key should not be unique
        assert (
            IdempotencyKeyValidator.validate_key_uniqueness(existing_keys, "key1")
            is False
        )

    def test_should_regenerate_key(self):
        """Test key regeneration logic."""
        now = datetime.now(timezone.utc)

        # Immutable operations should never regenerate
        assert (
            IdempotencyKeyValidator.should_regenerate_key("email", "create", now)
            is False
        )

        # Mutable operations should regenerate after TTL
        old_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)  # Very old
        assert (
            IdempotencyKeyValidator.should_regenerate_key("email", "update", old_time)
            is True
        )


class TestRedisReferencePattern:
    """Test Redis reference pattern functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        return Mock()

    @pytest.fixture
    def redis_reference(self, mock_redis):
        """Create RedisReferencePattern instance with mock Redis."""
        return RedisReferencePattern(mock_redis)

    def test_key_patterns(self, redis_reference):
        """Test key pattern definitions."""
        patterns = redis_reference.KEY_PATTERNS

        assert "office" in patterns
        assert "email" in patterns
        assert "calendar" in patterns
        assert "idempotency" in patterns

    def test_ttl_settings(self, redis_reference):
        """Test TTL settings."""
        ttl_settings = redis_reference.TTL_SETTINGS

        assert ttl_settings["office"] == 86400 * 7  # 7 days
        assert ttl_settings["email"] == 86400 * 30  # 30 days
        assert ttl_settings["idempotency"] == 86400  # 24 hours

    def test_store_large_payload(self, redis_reference):
        """Test storing large payloads."""
        payload = {"type": "email", "content": "test content"}

        redis_key = redis_reference.store_large_payload(
            "email", "user123", "email123", payload, "gmail"
        )

        assert redis_key.startswith("email:user123:gmail:")
        redis_reference.redis.setex.assert_called_once()

    def test_store_idempotency_key(self, redis_reference):
        """Test storing idempotency keys."""
        metadata = {"user_id": "user123", "operation": "create"}

        result = redis_reference.store_idempotency_key("key123", metadata)

        assert result is True
        redis_reference.redis.setex.assert_called_once()

    def test_check_idempotency_key(self, redis_reference):
        """Test checking idempotency keys."""
        metadata = {"user_id": "user123", "operation": "create"}
        redis_reference.redis.get.return_value = json.dumps(metadata)

        result = redis_reference.check_idempotency_key("key123")

        assert result == metadata
        redis_reference.redis.get.assert_called_once()

    def test_store_batch_reference(self, redis_reference):
        """Test storing batch references."""
        batch_data = {"batch_id": "batch123", "count": 100}

        redis_key = redis_reference.store_batch_reference(
            "batch123", "corr123", batch_data
        )

        assert redis_key.startswith("batch:batch123:corr123")
        redis_reference.redis.setex.assert_called_once()

    def test_validate_key_pattern(self, redis_reference):
        """Test key pattern validation."""
        # Valid pattern
        assert (
            redis_reference.validate_key_pattern(
                "email", user_id="user123", provider="gmail", doc_id="msg123"
            )
            is True
        )

        # Invalid pattern (missing required parameters)
        assert redis_reference.validate_key_pattern("email", user_id="user123") is False

    def test_generate_reference_id(self, redis_reference):
        """Test reference ID generation."""
        ref_id = redis_reference.generate_reference_id("test")

        assert ref_id.startswith("test_")
        assert len(ref_id) == 21  # prefix + 16 hex chars + underscore

    def test_get_key_info(self, redis_reference):
        """Test getting key information."""
        redis_reference.redis.ttl.return_value = 3600
        redis_reference.redis.type.return_value = "string"
        redis_reference.redis.get.return_value = b"test_value"

        info = redis_reference.get_key_info("test_key")

        assert "ttl" in info
        assert "type" in info
        assert "size" in info
        redis_reference.redis.ttl.assert_called_once()


class TestIdempotencyService:
    """Test idempotency service functionality."""

    @pytest.fixture
    def mock_redis_reference(self):
        """Create a mock RedisReferencePattern."""
        return Mock()

    @pytest.fixture
    def idempotency_service(self, mock_redis_reference):
        """Create IdempotencyService instance."""
        return IdempotencyService(mock_redis_reference)

    @pytest.fixture
    def sample_email_event(self):
        """Create a sample email event."""
        return EmailEvent(
            metadata=EventMetadata(
                event_id="event123",
                source_service="test-service",
                source_version="1.0.0",
            ),
            user_id="user123",
            email=EmailData(
                id="email123",
                thread_id="thread123",
                subject="Test",
                body="Test body",
                from_address="sender@example.com",
                to_addresses=[],
                cc_addresses=[],
                received_date=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                provider="gmail",
                provider_message_id="msg123",
            ),
            operation="create",
            batch_id="batch123",
            last_updated=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            sync_timestamp=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            provider="gmail",
            sync_type="backfill",
        )

    def test_process_event_with_idempotency(
        self, idempotency_service, sample_email_event
    ):
        """Test processing events with idempotency."""
        # Mock Redis to return no existing key
        idempotency_service.redis_reference.check_idempotency_key.return_value = None

        def mock_processor(event):
            return {"status": "processed", "event_id": event.metadata.event_id}

        result = idempotency_service.process_event_with_idempotency(
            sample_email_event, mock_processor
        )

        assert result["success"] is True
        assert result["idempotent"] is False
        # store_idempotency_key is called twice: once before processing, once after
        assert idempotency_service.redis_reference.store_idempotency_key.call_count == 2

    def test_process_event_already_processed(
        self, idempotency_service, sample_email_event
    ):
        """Test processing events that were already processed."""
        # Mock Redis to return existing key
        idempotency_service.redis_reference.check_idempotency_key.return_value = {
            "status": "completed",
            "result": {"status": "already_processed"},
        }

        def mock_processor(event):
            return {"status": "processed", "event_id": event.metadata.event_id}

        result = idempotency_service.process_event_with_idempotency(
            sample_email_event, mock_processor
        )

        assert result["success"] is True
        assert result["idempotent"] is True
        idempotency_service.redis_reference.store_idempotency_key.assert_not_called()

    def test_process_batch_with_idempotency(self, idempotency_service):
        """Test processing batches with idempotency."""
        batch_id = "batch123"
        correlation_id = "corr123"
        events = [Mock(), Mock(), Mock()]

        # Mock Redis to return no existing batch
        idempotency_service.redis_reference.retrieve_batch_reference.return_value = None

        def mock_processor(batch_id, correlation_id, events):
            return {"status": "processed", "count": len(events)}

        result = idempotency_service.process_batch_with_idempotency(
            batch_id, correlation_id, events, mock_processor
        )

        assert result["success"] is True
        assert result["batch_id"] == batch_id
        assert result["correlation_id"] == correlation_id

    def test_validate_idempotency_config(self, idempotency_service):
        """Test idempotency configuration validation."""
        config = idempotency_service.validate_idempotency_config("email", "create")

        assert config["event_type"] == "email"
        assert config["operation"] == "create"
        assert config["strategy"] == "immutable"
        assert config["valid"] is True

    def test_simulate_event_processing(self):
        """Test event processing simulation using test helper."""
        from services.common.tests.helpers.idempotency_test_helpers import (
            simulate_event_processing,
        )

        result = simulate_event_processing(
            "email", "create", "user123", "gmail", "email123"
        )

        assert result["simulation"] is True
        assert result["event_type"] == "email"
        assert result["operation"] == "create"
        assert result["user_id"] == "user123"
        assert result["provider"] == "gmail"
        assert result["event_id"] == "email123"
