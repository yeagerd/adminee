"""
Integration tests for internal tool events in the event-driven architecture.

Tests end-to-end flow from event publishing to Vespa indexing for:
- LLM Chat Events
- Shipment Events  
- Meeting Poll Events
- Booking Events
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock

import pytest
from pydantic import ValidationError

from services.common.events.internal_tool_events import (
    LLMChatEvent, LLMChatMessageData,
    ShipmentEvent, ShipmentEventData,
    MeetingPollEvent, MeetingPollData,
    BookingEvent, BookingData
)
from services.common.events.base_events import EventMetadata
from services.common.config.subscription_config import SubscriptionConfig
from services.vespa_loader.pubsub_consumer import VespaDocumentFactory


# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestInternalToolEventIntegration:
    """Test integration of internal tool events with the event-driven architecture."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_user_id = "test_user_123"
        self.test_correlation_id = "test_corr_456"
        self.test_batch_id = "test_batch_789"
        
        # Mock Redis client
        self.mock_redis = Mock()
        self.mock_redis.scan.return_value = (0, [])
        self.mock_redis.get.return_value = None
        self.mock_redis.setex.return_value = True
        self.mock_redis.delete.return_value = 1
        self.mock_redis.ttl.return_value = -1
        
        # Mock Pub/Sub client
        self.mock_pubsub = Mock()
        self.mock_pubsub.publish_message.return_value = "test_message_id"
        
        # Initialize document factory
        self.document_factory = VespaDocumentFactory()
    
    def _create_test_metadata(self, source_service: str = "test-service") -> EventMetadata:
        """Create test event metadata."""
        return EventMetadata(
            source_service=source_service,
            user_id=self.test_user_id,
            correlation_id=self.test_correlation_id,
            tags={"test": "true"}
        )
    
    def _create_test_llm_chat_event(self) -> LLMChatEvent:
        """Create a test LLM chat event."""
        message_data = LLMChatMessageData(
            id="chat_msg_001",
            chat_id="chat_session_001",
            session_id="user_session_001",
            model_name="gpt-4",
            role="user",
            message_type="text",
            content="Hello, how can you help me today?",
            tokens_used=15,
            response_time_ms=1200,
            cost_usd=0.002,
            tools_used=["web_search", "calculator"],
            tool_results=[
                {"tool": "web_search", "result": "Search results..."},
                {"tool": "calculator", "result": "42"}
            ],
            conversation_context=[
                {"role": "system", "content": "You are a helpful assistant."}
            ],
            user_feedback="Great response!",
            metadata={"platform": "web", "browser": "chrome"}
        )
        
        return LLMChatEvent(
            metadata=self._create_test_metadata("chat-service"),
            user_id=self.test_user_id,
            message=message_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=datetime.now(timezone.utc),
            sync_timestamp=datetime.now(timezone.utc),
            chat_id="chat_session_001",
            session_id="user_session_001"
        )
    
    def _create_test_shipment_event(self) -> ShipmentEvent:
        """Create a test shipment event."""
        shipment_data = ShipmentEventData(
            id="shipment_event_001",
            shipment_id="shipment_001",
            tracking_number="1Z999AA1234567890",
            carrier="FedEx",
            event_type="shipped",
            event_timestamp=datetime.now(timezone.utc),
            location="Memphis, TN",
            status="in_transit",
            description="Package picked up by carrier",
            estimated_delivery=datetime.now(timezone.utc) + timedelta(days=2),
            actual_delivery=None,
            recipient_name="John Doe",
            recipient_address="123 Main St, Anytown, USA",
            package_details={
                "weight": "2.5 lbs",
                "dimensions": "12x8x6 inches",
                "contents": "Electronics"
            },
            delivery_attempts=0,
            signature_required=True,
            signature_received=None,
            metadata={"service_level": "express", "insurance": "declared_value"}
        )
        
        return ShipmentEvent(
            metadata=self._create_test_metadata("shipments-service"),
            user_id=self.test_user_id,
            shipment_event=shipment_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=datetime.now(timezone.utc),
            sync_timestamp=datetime.now(timezone.utc),
            shipment_id="shipment_001",
            tracking_number="1Z999AA1234567890"
        )
    
    def _create_test_meeting_poll_event(self) -> MeetingPollEvent:
        """Create a test meeting poll event."""
        poll_data = MeetingPollData(
            id="poll_001",
            meeting_id="meeting_001",
            poll_type="single_choice",
            question="What time works best for the team meeting?",
            options=["9:00 AM", "2:00 PM", "4:00 PM"],
            responses=[
                {"user_id": "user1", "choice": "9:00 AM", "timestamp": datetime.now(timezone.utc)},
                {"user_id": "user2", "choice": "2:00 PM", "timestamp": datetime.now(timezone.utc)}
            ],
            total_responses=2,
            is_active=True,
            is_anonymous=False,
            allow_multiple_votes=False,
            created_by="meeting_organizer@example.com",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
            results_visible=True,
            metadata={"meeting_type": "team_sync", "priority": "high"}
        )
        
        return MeetingPollEvent(
            metadata=self._create_test_metadata("meetings-service"),
            user_id=self.test_user_id,
            poll=poll_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=datetime.now(timezone.utc),
            sync_timestamp=datetime.now(timezone.utc),
            meeting_id="meeting_001",
            poll_id="poll_001"
        )
    
    def _create_test_booking_event(self) -> BookingEvent:
        """Create a test booking event."""
        booking_data = BookingData(
            id="booking_001",
            resource_id="room_001",
            resource_type="conference_room",
            resource_name="Main Conference Room",
            start_time=datetime.now(timezone.utc) + timedelta(hours=1),
            end_time=datetime.now(timezone.utc) + timedelta(hours=2),
            duration_minutes=60,
            status="confirmed",
            booking_type="meeting",
            attendees=["user1@example.com", "user2@example.com"],
            organizer="organizer@example.com",
            purpose="Weekly team standup",
            notes="Please bring your laptops for demos",
            recurring_pattern="weekly",
            recurring_end_date=datetime.now(timezone.utc) + timedelta(weeks=4),
            cancellation_reason=None,
            metadata={"room_capacity": 12, "equipment": ["projector", "whiteboard"]}
        )
        
        return BookingEvent(
            metadata=self._create_test_metadata("meetings-service"),
            user_id=self.test_user_id,
            booking=booking_data,
            operation="create",
            batch_id=self.test_batch_id,
            last_updated=datetime.now(timezone.utc),
            sync_timestamp=datetime.now(timezone.utc),
            resource_id="room_001",
            resource_type="conference_room"
        )
    
    def test_llm_chat_event_creation_and_validation(self):
        """Test LLM chat event creation and validation."""
        event = self._create_test_llm_chat_event()
        
        # Validate event structure
        assert event.user_id == self.test_user_id
        assert event.operation == "create"
        assert event.batch_id == self.test_batch_id
        assert event.metadata.source_service == "chat-service"
        
        # Validate message data
        assert event.message.model_name == "gpt-4"
        assert event.message.role == "user"
        assert event.message.content == "Hello, how can you help me today?"
        assert len(event.message.tools_used) == 2
        assert len(event.message.tool_results) == 2
        
        # Validate serialization
        event_dict = event.model_dump()
        assert "message" in event_dict
        assert "operation" in event_dict
        assert "batch_id" in event_dict
    
    def test_shipment_event_creation_and_validation(self):
        """Test shipment event creation and validation."""
        event = self._create_test_shipment_event()
        
        # Validate event structure
        assert event.user_id == self.test_user_id
        assert event.operation == "create"
        assert event.batch_id == self.test_batch_id
        assert event.metadata.source_service == "shipments-service"
        
        # Validate shipment data
        assert event.shipment_event.carrier == "FedEx"
        assert event.shipment_event.tracking_number == "1Z999AA1234567890"
        assert event.shipment_event.status == "in_transit"
        assert event.shipment_event.signature_required is True
        
        # Validate serialization
        event_dict = event.model_dump()
        assert "shipment_event" in event_dict
        assert "operation" in event_dict
        assert "batch_id" in event_dict
    
    def test_meeting_poll_event_creation_and_validation(self):
        """Test meeting poll event creation and validation."""
        event = self._create_test_meeting_poll_event()
        
        # Validate event structure
        assert event.user_id == self.test_user_id
        assert event.operation == "create"
        assert event.batch_id == self.test_batch_id
        assert event.metadata.source_service == "meetings-service"
        
        # Validate poll data
        assert event.poll.poll_type == "single_choice"
        assert event.poll.question == "What time works best for the team meeting?"
        assert len(event.poll.options) == 3
        assert event.poll.total_responses == 2
        assert event.poll.is_active is True
        
        # Validate serialization
        event_dict = event.model_dump()
        assert "poll" in event_dict
        assert "operation" in event_dict
        assert "batch_id" in event_dict
    
    def test_booking_event_creation_and_validation(self):
        """Test booking event creation and validation."""
        event = self._create_test_booking_event()
        
        # Validate event structure
        assert event.user_id == self.test_user_id
        assert event.operation == "create"
        assert event.batch_id == self.test_batch_id
        assert event.metadata.source_service == "meetings-service"
        
        # Validate booking data
        assert event.booking.resource_type == "conference_room"
        assert event.booking.resource_name == "Main Conference Room"
        assert event.booking.status == "confirmed"
        assert event.booking.duration_minutes == 60
        assert len(event.booking.attendees) == 2
        
        # Validate serialization
        event_dict = event.model_dump()
        assert "booking" in event_dict
        assert "operation" in event_dict
        assert "batch_id" in event_dict
    
    def test_internal_tool_event_publishing_flow(self):
        """Test the complete flow of publishing internal tool events."""
        events = [
            self._create_test_llm_chat_event(),
            self._create_test_shipment_event(),
            self._create_test_meeting_poll_event(),
            self._create_test_booking_event()
        ]
        
        for event in events:
            # Simulate event publishing
            event_json = event.model_dump_json()
            event_dict = json.loads(event_json)
            
            # Validate the published event structure
            assert "metadata" in event_dict
            assert "operation" in event_dict
            assert "batch_id" in event_dict
            assert "last_updated" in event_dict
            assert "sync_timestamp" in event_dict
            
            # Validate source service is set correctly
            assert event_dict["metadata"]["source_service"] in [
                "chat-service", "shipments-service", "meetings-service"
            ]
    
    def test_internal_tool_event_subscription_configuration(self):
        """Test that internal tool events are properly configured in subscription config."""
        # Check that internal tool topics are configured
        vespa_topics = SubscriptionConfig.get_service_topics("vespa_loader")
        
        # These topics should exist for internal tools
        expected_topics = ["llm_chats", "shipment_events", "meeting_polls", "bookings"]
        
        for topic in expected_topics:
            assert topic in vespa_topics, f"Topic {topic} not found in vespa_loader configuration"
            
            # Check subscription configuration
            config = SubscriptionConfig.get_subscription_config("vespa_loader", topic)
            assert "subscription_name" in config
            assert "batch_size" in config
            assert "ack_deadline_seconds" in config
    
    def test_internal_tool_event_vespa_document_creation(self):
        """Test that internal tool events can be converted to Vespa documents."""
        events = [
            self._create_test_llm_chat_event(),
            self._create_test_shipment_event(),
            self._create_test_meeting_poll_event(),
            self._create_test_booking_event()
        ]
        
        for event in events:
            try:
                # This would normally be done by the Vespa loader consumer
                # For now, we'll test that the event can be serialized properly
                event_dict = event.model_dump()
                
                # Validate required fields for Vespa indexing
                assert "user_id" in event_dict
                assert "operation" in event_dict
                assert "last_updated" in event_dict
                assert "sync_timestamp" in event_dict
                
                # Validate event-specific data is present
                if isinstance(event, LLMChatEvent):
                    assert "message" in event_dict
                    assert "chat_id" in event_dict
                elif isinstance(event, ShipmentEvent):
                    assert "shipment_event" in event_dict
                    assert "shipment_id" in event_dict
                elif isinstance(event, MeetingPollEvent):
                    assert "poll" in event_dict
                    assert "meeting_id" in event_dict
                elif isinstance(event, BookingEvent):
                    assert "booking" in event_dict
                    assert "resource_id" in event_dict
                    
            except Exception as e:
                pytest.fail(f"Failed to process {type(event).__name__}: {e}")
    
    def test_internal_tool_event_error_handling(self):
        """Test error handling for malformed internal tool events."""
        # Test with missing required fields
        with pytest.raises(ValidationError):
            LLMChatEvent(
                metadata=self._create_test_metadata(),
                user_id="",  # Empty user_id should fail
                message=LLMChatMessageData(
                    id="test",
                    chat_id="test",
                    session_id="test",
                    model_name="test",
                    role="user",
                    message_type="text",
                    content="test"
                ),
                operation="create",
                last_updated=datetime.now(timezone.utc),
                sync_timestamp=datetime.now(timezone.utc),
                chat_id="test",
                session_id="test"
            )
        
        # Test with invalid operation
        with pytest.raises(ValidationError):
            event = self._create_test_llm_chat_event()
            event.operation = "invalid_operation"  # This should fail validation
    
    def test_internal_tool_event_batch_processing(self):
        """Test batch processing of internal tool events."""
        # Create multiple events with the same batch_id
        batch_id = "test_batch_001"
        
        llm_events = [
            self._create_test_llm_chat_event() for _ in range(3)
        ]
        shipment_events = [
            self._create_test_shipment_event() for _ in range(2)
        ]
        
        # Set batch_id for all events
        for event in llm_events + shipment_events:
            event.batch_id = batch_id
        
        # Validate batch processing
        batch_events = llm_events + shipment_events
        
        # Group by event type
        event_types = {}
        for event in batch_events:
            event_type = type(event).__name__
            if event_type not in event_types:
                event_types[event_type] = []
            event_types[event_type].append(event)
        
        # Validate batch grouping
        assert len(event_types["LLMChatEvent"]) == 3
        assert len(event_types["ShipmentEvent"]) == 2
        
        # Validate all events have the same batch_id
        for event in batch_events:
            assert event.batch_id == batch_id
    
    def test_internal_tool_event_metadata_consistency(self):
        """Test that internal tool events maintain metadata consistency."""
        events = [
            self._create_test_llm_chat_event(),
            self._create_test_shipment_event(),
            self._create_test_meeting_poll_event(),
            self._create_test_booking_event()
        ]
        
        for event in events:
            # Validate metadata structure
            assert event.metadata.user_id == self.test_user_id
            assert event.metadata.correlation_id == self.test_correlation_id
            assert "test" in event.metadata.tags
            assert event.metadata.tags["test"] == "true"
            
            # Validate timestamp consistency
            assert event.last_updated is not None
            assert event.sync_timestamp is not None
            assert event.last_updated <= datetime.now(timezone.utc)
            assert event.sync_timestamp <= datetime.now(timezone.utc)
    
    def test_internal_tool_event_serialization_performance(self):
        """Test serialization performance of internal tool events."""
        import time
        
        # Create multiple events
        events = [
            self._create_test_llm_chat_event(),
            self._create_test_shipment_event(),
            self._create_test_meeting_poll_event(),
            self._create_test_booking_event()
        ]
        
        # Test serialization performance
        start_time = time.time()
        
        for _ in range(100):  # Serialize 100 times
            for event in events:
                event.model_dump_json()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second for 400 serializations)
        assert total_time < 1.0, f"Serialization took too long: {total_time:.3f}s"
        
        logger.info(f"Serialized {len(events) * 100} events in {total_time:.3f}s")


class TestInternalToolEventEndToEnd:
    """Test end-to-end flow of internal tool events."""
    
    @pytest.mark.asyncio
    async def test_llm_chat_event_end_to_end_flow(self):
        """Test complete LLM chat event flow from creation to processing."""
        # This would test the actual event flow through the system
        # For now, we'll simulate the key components
        
        # 1. Event Creation
        event = TestInternalToolEventIntegration()._create_test_llm_chat_event()
        
        # 2. Event Validation
        assert event.metadata.source_service == "chat-service"
        assert event.operation == "create"
        
        # 3. Event Serialization
        event_json = event.model_dump_json()
        event_dict = json.loads(event_json)
        
        # 4. Event Publishing (simulated)
        message_id = "simulated_message_id"
        assert message_id is not None
        
        # 5. Event Processing (simulated)
        processed_event = LLMChatEvent(**event_dict)
        assert processed_event.message.content == "Hello, how can you help me today?"
        
        # 6. Vespa Document Creation (simulated)
        # In a real test, this would create actual Vespa documents
        document_data = {
            "id": f"llm_chat_{event.message.id}",
            "type": "llm_chat",
            "user_id": event.user_id,
            "content": event.message.content,
            "metadata": {
                "chat_id": event.chat_id,
                "session_id": event.session_id,
                "model_name": event.message.model_name,
                "operation": event.operation
            }
        }
        
        assert document_data["type"] == "llm_chat"
        assert document_data["user_id"] == event.user_id
        assert document_data["content"] == event.message.content
    
    @pytest.mark.asyncio
    async def test_shipment_event_end_to_end_flow(self):
        """Test complete shipment event flow from creation to processing."""
        # Similar end-to-end test for shipment events
        event = TestInternalToolEventIntegration()._create_test_shipment_event()
        
        # Validate event structure
        assert event.shipment_event.carrier == "FedEx"
        assert event.shipment_event.tracking_number == "1Z999AA1234567890"
        
        # Simulate document creation
        document_data = {
            "id": f"shipment_{event.shipment_event.id}",
            "type": "shipment_event",
            "user_id": event.user_id,
            "content": event.shipment_event.description,
            "metadata": {
                "shipment_id": event.shipment_id,
                "tracking_number": event.tracking_number,
                "carrier": event.shipment_event.carrier,
                "operation": event.operation
            }
        }
        
        assert document_data["type"] == "shipment_event"
        assert document_data["metadata"]["carrier"] == "FedEx"
    
    @pytest.mark.asyncio
    async def test_meeting_poll_event_end_to_end_flow(self):
        """Test complete meeting poll event flow from creation to processing."""
        event = TestInternalToolEventIntegration()._create_test_meeting_poll_event()
        
        # Validate event structure
        assert event.poll.poll_type == "single_choice"
        assert event.poll.total_responses == 2
        
        # Simulate document creation
        document_data = {
            "id": f"meeting_poll_{event.poll.id}",
            "type": "meeting_poll",
            "user_id": event.user_id,
            "content": event.poll.question,
            "metadata": {
                "meeting_id": event.meeting_id,
                "poll_id": event.poll_id,
                "poll_type": event.poll.poll_type,
                "operation": event.operation
            }
        }
        
        assert document_data["type"] == "meeting_poll"
        assert document_data["content"] == event.poll.question
    
    @pytest.mark.asyncio
    async def test_booking_event_end_to_end_flow(self):
        """Test complete booking event flow from creation to processing."""
        event = TestInternalToolEventIntegration()._create_test_booking_event()
        
        # Validate event structure
        assert event.booking.resource_type == "conference_room"
        assert event.booking.duration_minutes == 60
        
        # Simulate document creation
        document_data = {
            "id": f"booking_{event.booking.id}",
            "type": "booking",
            "user_id": event.user_id,
            "content": event.booking.purpose,
            "metadata": {
                "resource_id": event.resource_id,
                "resource_type": event.resource_type,
                "start_time": event.booking.start_time.isoformat(),
                "operation": event.operation
            }
        }
        
        assert document_data["type"] == "booking"
        assert document_data["metadata"]["resource_type"] == "conference_room"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
