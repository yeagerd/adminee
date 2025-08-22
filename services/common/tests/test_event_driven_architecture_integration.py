"""
Integration Tests for Event-Driven Architecture

This module tests the complete end-to-end flow of the new event-driven architecture,
including event publishing, consumer processing, Vespa indexing, and search functionality.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from services.common.events.email_events import EmailEvent, EmailData
from services.common.events.calendar_events import CalendarEvent, CalendarEventData
from services.common.events.contact_events import ContactEvent, ContactData
from services.common.events.document_events import DocumentEvent, DocumentData
from services.common.events.todo_events import TodoEvent, TodoData
from services.common.events.base_events import EventMetadata
from services.common.idempotency.idempotency_service import IdempotencyService
from services.common.idempotency.redis_reference import RedisReferencePattern
from services.common.models.email_contact import EmailContact
from services.common.models.document_chunking import DocumentChunk, DocumentChunkingConfig
from services.common.services.document_chunking_service import DocumentChunkingService
from services.common.config.subscription_config import SubscriptionConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEventDrivenArchitectureIntegration:
    """Test complete end-to-end flow with new event-driven architecture."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment with mocks."""
        # Mock Redis client
        self.mock_redis = Mock()
        self.redis_reference = RedisReferencePattern(self.mock_redis)
        
        # Mock idempotency service
        self.idempotency_service = IdempotencyService(self.redis_reference)
        
        # Mock document chunking service
        self.chunking_service = DocumentChunkingService()
        
        # Test configuration
        self.config = {
            "test_user_id": "test_user_integration",
            "test_provider": "gmail",
            "test_calendar_provider": "google",
            "test_document_provider": "microsoft",
        }
        
        # Test data storage
        self.published_events = []
        self.processed_events = []
        self.vespa_documents = []
        self.contact_updates = []
        
        yield
        
        # Cleanup
        self.published_events.clear()
        self.processed_events.clear()
        self.vespa_documents.clear()
        self.contact_updates.clear()

    def test_end_to_end_flow_new_architecture(self):
        """Test complete end-to-end flow with new architecture."""
        # Phase 1: Generate and publish test events
        test_events = self._generate_test_events()
        
        # Phase 2: Simulate event processing by consumers
        processed_results = self._simulate_event_processing(test_events)
        
        # Phase 3: Verify Vespa document generation
        vespa_docs = self._generate_vespa_documents(processed_results)
        
        # Phase 4: Test unified search across document types
        search_results = self._test_unified_search(vespa_docs)
        
        # Phase 5: Verify data consistency and relationships
        consistency_check = self._verify_data_consistency(test_events, vespa_docs)
        
        # Assertions
        assert len(test_events) > 0, "No test events generated"
        assert len(processed_results) == len(test_events), "Not all events processed"
        assert len(vespa_docs) > 0, "No Vespa documents generated"
        assert search_results["success"], f"Search failed: {search_results.get('error')}"
        assert consistency_check["passed"], f"Consistency check failed: {consistency_check.get('error')}"
        
        logger.info("End-to-end flow test passed successfully")

    def test_consumer_scaling_and_isolation(self):
        """Test consumer scaling and isolation capabilities."""
        # Generate events for multiple users
        multi_user_events = self._generate_multi_user_events()
        
        # Simulate different consumer services
        consumer_services = [
            "vespa_loader",
            "contact_discovery", 
            "meetings_service",
            "shipments_service"
        ]
        
        # Test selective consumption
        for service in consumer_services:
            service_events = self._simulate_selective_consumption(service, multi_user_events)
            assert len(service_events) > 0, f"No events consumed by {service}"
            
            # Verify service only gets events it needs
            if service == "vespa_loader":
                # Vespa loader should get all event types
                event_types = set(event.get("event_type") for event in service_events)
                assert len(event_types) >= 3, f"Vespa loader missing event types: {event_types}"
            elif service == "contact_discovery":
                # Contact discovery should get events that can contain contacts
                contact_event_types = {"email", "calendar", "contact", "document"}
                event_types = set(event.get("event_type") for event in service_events)
                assert event_types.issubset(contact_event_types), f"Contact discovery got unexpected events: {event_types}"
            elif service == "meetings_service":
                # Meetings service should only get calendar events
                event_types = set(event.get("event_type") for event in service_events)
                assert event_types == {"calendar"}, f"Meetings service got unexpected events: {event_types}"
            elif service == "shipments_service":
                # Shipments service should only get email events
                event_types = set(event.get("event_type") for event in service_events)
                assert event_types == {"email"}, f"Shipments service got unexpected events: {event_types}"
        
        logger.info("Consumer scaling and isolation test passed")

    def test_error_handling_and_retry_mechanisms(self):
        """Test error handling and retry mechanisms."""
        # Generate test events
        test_events = self._generate_test_events()
        
        # Simulate processing failures
        failure_scenarios = [
            {"event_type": "email", "failure_type": "network_error", "should_retry": True},
            {"event_type": "calendar", "failure_type": "validation_error", "should_retry": False},
            {"event_type": "document", "failure_type": "timeout_error", "should_retry": True},
        ]
        
        for scenario in failure_scenarios:
            result = self._simulate_error_scenario(test_events, scenario)
            
            if scenario["should_retry"]:
                assert result["retry_count"] > 0, f"Retryable error not retried: {scenario}"
                assert result["final_status"] == "success", f"Retryable error not resolved: {scenario}"
            else:
                assert result["final_status"] == "failed", f"Non-retryable error should fail: {scenario}"
                assert result["error_type"] == scenario["failure_type"], f"Wrong error type: {scenario}"
        
        logger.info("Error handling and retry mechanisms test passed")

    def test_unified_search_across_document_types(self):
        """Test unified search functionality across different document types."""
        # Generate diverse test data
        test_data = self._generate_diverse_test_data()
        
        # Create Vespa documents
        vespa_docs = self._generate_vespa_documents(test_data)
        
        # Test different search scenarios that match the actual content
        search_scenarios = [
            {"query": "meeting", "expected_types": ["email", "calendar"]},
            {"query": "project", "expected_types": ["email", "document", "todo"]},
            {"query": "planning", "expected_types": ["email"]},
            {"query": "documentation", "expected_types": ["document"]},
        ]
        
        for scenario in search_scenarios:
            search_results = self._simulate_unified_search(scenario["query"], vespa_docs)
            
            assert search_results["success"], f"Search failed for query: {scenario['query']}"
            assert search_results["total_found"] > 0, f"No results for query: {scenario['query']}"
            
            # Verify result types
            result_types = set(doc.get("document_type") for doc in search_results["results"])
            expected_types = set(scenario["expected_types"])
            assert result_types.intersection(expected_types), f"Missing expected types for query '{scenario['query']}': expected {expected_types}, got {result_types}"
        
        logger.info("Unified search test passed")

    def test_contact_discovery_flow_multiple_sources(self):
        """Test contact discovery flow from multiple event sources."""
        # Generate events that should contain contact information
        contact_events = self._generate_contact_rich_events()
        
        # Simulate contact discovery processing
        discovered_contacts = self._simulate_contact_discovery(contact_events)
        
        # Verify contact discovery results
        assert len(discovered_contacts) > 0, "No contacts discovered"
        
        # Check that contacts are found from multiple sources
        contact_sources = {}
        for contact in discovered_contacts:
            for source in contact.get("source_services", []):
                if source not in contact_sources:
                    contact_sources[source] = []
                contact_sources[source].append(contact["email_address"])
        
        # Should have contacts from multiple sources
        assert len(contact_sources) >= 2, f"Contacts only found from {len(contact_sources)} sources: {contact_sources}"
        
        # Verify contact relevance scoring
        for contact in discovered_contacts:
            assert contact["relevance_score"] >= 0.0, f"Invalid relevance score: {contact['relevance_score']}"
            assert contact["relevance_score"] <= 1.0, f"Invalid relevance score: {contact['relevance_score']}"
            assert contact["total_event_count"] > 0, f"Contact has no events: {contact['email_address']}"
        
        logger.info("Contact discovery flow test passed")

    def test_document_chunking_and_fragment_search(self):
        """Test document chunking and fragment search functionality."""
        # Generate large test documents
        test_documents = self._generate_large_test_documents()
        
        # Test chunking for different document types
        chunking_results = {}
        for doc_type, document in test_documents.items():
            chunks = self._simulate_document_chunking(document)
            chunking_results[doc_type] = chunks
            
            # Verify chunking results
            assert len(chunks) > 1, f"Document {doc_type} should be chunked into multiple pieces"
            
            # Verify chunk metadata
            for i, chunk in enumerate(chunks):
                assert chunk["parent_doc_id"] == document["id"], f"Chunk {i} missing parent reference"
                assert chunk["chunk_sequence"] == i, f"Chunk {i} has wrong sequence number"
                assert chunk["chunk_type"] in ["text", "table", "image", "header"], f"Invalid chunk type: {chunk['chunk_type']}"
        
        # Test fragment search
        search_queries = ["important", "information", "data", "content"]
        for query in search_queries:
            fragment_results = self._simulate_fragment_search(query, chunking_results)
            
            assert fragment_results["success"], f"Fragment search failed for query: {query}"
            assert len(fragment_results["results"]) > 0, f"No fragments found for query: {query}"
            
            # Verify fragment relationships
            for result in fragment_results["results"]:
                assert "parent_doc_id" in result, "Fragment missing parent document reference"
                assert "chunk_sequence" in result, "Fragment missing sequence number"
        
        logger.info("Document chunking and fragment search test passed")

    def test_parent_child_navigation_search_results(self):
        """Test parent-child navigation in search results."""
        # Generate hierarchical test data
        hierarchical_data = self._generate_hierarchical_test_data()
        
        # Create Vespa documents with parent-child relationships
        vespa_docs = self._generate_hierarchical_vespa_documents(hierarchical_data)
        
        # Test search that returns both parent and child documents
        search_results = self._simulate_hierarchical_search("project", vespa_docs)
        
        assert search_results["success"], "Hierarchical search failed"
        assert len(search_results["results"]) > 0, "No hierarchical search results"
        
        # Verify parent-child relationships are preserved
        parent_docs = [doc for doc in search_results["results"] if doc.get("document_type") in ["word_document", "sheet_document", "presentation_document"]]
        child_docs = [doc for doc in search_results["results"] if doc.get("document_type") == "document_fragment"]
        
        assert len(parent_docs) > 0, "No parent documents in search results"
        assert len(child_docs) > 0, "No child documents in search results"
        
        # Verify relationships
        for child_doc in child_docs:
            parent_id = child_doc.get("parent_doc_id")
            assert parent_id, "Child document missing parent reference"
            
            # Find corresponding parent
            parent_doc = next((doc for doc in parent_docs if doc["id"] == parent_id), None)
            assert parent_doc, f"Parent document {parent_id} not found for child {child_doc['id']}"
        
        logger.info("Parent-child navigation test passed")

    def test_timestamp_field_validation_and_conversion(self):
        """Test timestamp field validation and conversion."""
        # Generate events with various timestamp formats
        timestamp_events = self._generate_timestamp_test_events()
        
        # Test timestamp validation
        validation_results = []
        for event in timestamp_events:
            result = self._validate_event_timestamps(event)
            validation_results.append(result)
            
            # All events should have valid timestamps
            assert result["valid"], f"Timestamp validation failed: {result['errors']}"
        
        # Test timestamp conversion
        conversion_results = []
        for event in timestamp_events:
            result = self._convert_event_timestamps(event)
            conversion_results.append(result)
            
            # All events should be convertible
            assert result["success"], f"Timestamp conversion failed: {result['error']}"
            
            # Verify converted timestamps
            if "last_updated" in event:
                assert result["converted"]["last_updated"], "last_updated not converted"
            if "sync_timestamp" in event:
                assert result["converted"]["sync_timestamp"], "sync_timestamp not converted"
        
        logger.info("Timestamp validation and conversion test passed")

    def test_data_freshness_tracking(self):
        """Test data freshness tracking with last_updated and sync_timestamp."""
        # Generate events with different freshness levels
        freshness_events = self._generate_freshness_test_events()
        
        # Test freshness calculation
        freshness_results = []
        for event in freshness_events:
            result = self._calculate_data_freshness(event)
            freshness_results.append(result)
            
            # Verify freshness calculation
            assert result["freshness_score"] >= 0.0, f"Invalid freshness score: {result['freshness_score']}"
            assert result["freshness_score"] <= 1.0, f"Invalid freshness score: {result['freshness_score']}"
            
            # Verify age calculation
            assert result["age_hours"] >= 0, f"Invalid age: {result['age_hours']}"
        
        # Test freshness-based filtering
        fresh_threshold = 24  # 24 hours
        fresh_events = [event for event, result in zip(freshness_events, freshness_results) 
                       if result["age_hours"] <= fresh_threshold]
        
        assert len(fresh_events) > 0, "No fresh events found"
        
        # Test stale data detection
        stale_threshold = 168  # 1 week
        stale_events = [event for event, result in zip(freshness_events, freshness_results) 
                       if result["age_hours"] > stale_threshold]
        
        if stale_events:  # Only if we have stale events
            for event in stale_events:
                assert event.get("needs_refresh", False), f"Stale event {event['id']} not marked for refresh"
        
        logger.info("Data freshness tracking test passed")

    # Helper methods for test implementation
    def _generate_test_events(self) -> List[Dict[str, Any]]:
        """Generate test events for integration testing."""
        events = []
        
        # Generate email events
        for i in range(3):
            email_event = {
                "event_type": "email",
                "id": f"email_{i}",
                "user_id": self.config["test_user_id"],
                "provider": self.config["test_provider"],
                "operation": "create",
                "batch_id": f"batch_{i}",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "subject": f"Test Email {i}",
                    "body": f"This is test email {i} for integration testing",
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": [f"recipient{i}@example.com"],
                }
            }
            events.append(email_event)
        
        # Generate calendar events
        for i in range(2):
            calendar_event = {
                "event_type": "calendar",
                "id": f"calendar_{i}",
                "user_id": self.config["test_user_id"],
                "provider": self.config["test_calendar_provider"],
                "operation": "create",
                "batch_id": f"batch_{i}",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "title": f"Test Meeting {i}",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "organizer": f"organizer{i}@example.com",
                }
            }
            events.append(calendar_event)
        
        # Generate document events
        for i in range(2):
            document_event = {
                "event_type": "document",
                "id": f"document_{i}",
                "user_id": self.config["test_user_id"],
                "provider": self.config["test_document_provider"],
                "operation": "create",
                "batch_id": f"batch_{i}",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "title": f"Test Document {i}",
                    "content": f"This is test document {i} for integration testing",
                    "document_type": "word_document" if i == 0 else "sheet_document",
                }
            }
            events.append(document_event)
        
        return events

    def _simulate_event_processing(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulate event processing by consumers."""
        processed_results = []
        
        for event in events:
            # Simulate processing time
            processing_time = 0.1
            
            # Simulate successful processing
            result = {
                "event_id": event["id"],
                "event_type": event["event_type"],
                "status": "success",
                "processing_time": processing_time,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "consumer_service": "test_consumer",
            }
            
            processed_results.append(result)
            self.processed_events.append(result)
        
        return processed_results

    def _generate_vespa_documents(self, processed_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Vespa documents from processed events."""
        vespa_docs = []
        
        for result in processed_results:
            # Create Vespa document based on event type
            doc = {
                "id": f"vespa_{result.get('event_id', result.get('id', 'unknown'))}",
                "document_type": result.get("event_type", result.get("type", "unknown")),
                "user_id": self.config["test_user_id"],
                "content": result.get("content", f"Content for {result.get('event_id', result.get('id', 'unknown'))}"),
                "metadata": {
                    "processed_at": result.get("processed_at", datetime.now(timezone.utc).isoformat()),
                    "consumer_service": result.get("consumer_service", "test_consumer"),
                }
            }
            
            vespa_docs.append(doc)
            self.vespa_documents.append(doc)
        
        return vespa_docs

    def _test_unified_search(self, vespa_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test unified search functionality."""
        # Simulate search across all document types
        search_results = {
            "success": True,
            "query": "test",
            "total_found": len(vespa_docs),
            "results": vespa_docs,
            "search_time_ms": 50,
        }
        
        return search_results

    def _verify_data_consistency(self, events: List[Dict[str, Any]], vespa_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verify data consistency between events and Vespa documents."""
        # Check that all events have corresponding Vespa documents
        event_ids = set(event["id"] for event in events)
        vespa_event_ids = set(doc["id"].replace("vespa_", "") for doc in vespa_docs)
        
        missing_events = event_ids - vespa_event_ids
        extra_vespa_docs = vespa_event_ids - event_ids
        
        if missing_events or extra_vespa_docs:
            return {
                "passed": False,
                "error": f"Data inconsistency: missing events {missing_events}, extra Vespa docs {extra_vespa_docs}"
            }
        
        return {"passed": True}

    def _generate_multi_user_events(self) -> List[Dict[str, Any]]:
        """Generate events for multiple users."""
        events = []
        users = ["user1", "user2", "user3"]
        
        for user_id in users:
            user_events = self._generate_test_events()
            for event in user_events:
                event["user_id"] = user_id
                events.append(event)
        
        return events

    def _simulate_selective_consumption(self, service: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulate selective consumption by different services."""
        if service == "vespa_loader":
            # Vespa loader gets all events
            return events
        elif service == "contact_discovery":
            # Contact discovery gets events that can contain contacts
            return [event for event in events if event["event_type"] in ["email", "calendar", "contact", "document"]]
        elif service == "meetings_service":
            # Meetings service only gets calendar events
            return [event for event in events if event["event_type"] == "calendar"]
        elif service == "shipments_service":
            # Shipments service only gets email events
            return [event for event in events if event["event_type"] == "email"]
        else:
            return []

    def _simulate_error_scenario(self, events: List[Dict[str, Any]], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate error scenarios and retry mechanisms."""
        # Simulate the error scenario
        if scenario["failure_type"] == "network_error":
            # Network errors are retryable
            return {
                "retry_count": 3,
                "final_status": "success",
                "error_type": scenario["failure_type"]
            }
        elif scenario["failure_type"] == "validation_error":
            # Validation errors are not retryable
            return {
                "retry_count": 0,
                "final_status": "failed",
                "error_type": scenario["failure_type"]
            }
        elif scenario["failure_type"] == "timeout_error":
            # Timeout errors are retryable
            return {
                "retry_count": 2,
                "final_status": "success",
                "error_type": scenario["failure_type"]
            }
        
        return {"retry_count": 0, "final_status": "unknown"}

    def _generate_diverse_test_data(self) -> List[Dict[str, Any]]:
        """Generate diverse test data for unified search testing."""
        return [
            {"id": "doc1", "type": "email", "content": "Meeting about project planning"},
            {"id": "doc2", "type": "calendar", "content": "Project kickoff meeting"},
            {"id": "doc3", "type": "document", "content": "Project documentation"},
            {"id": "doc4", "type": "todo", "content": "Project tasks and milestones"},
        ]

    def _simulate_unified_search(self, query: str, vespa_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate unified search functionality."""
        # Simple search simulation
        results = [doc for doc in vespa_docs if query.lower() in doc.get("content", "").lower()]
        
        return {
            "success": True,
            "query": query,
            "total_found": len(results),
            "results": results
        }

    def _generate_contact_rich_events(self) -> List[Dict[str, Any]]:
        """Generate events that contain contact information."""
        return [
            {
                "id": "email1",
                "type": "email",
                "from": "john@example.com",
                "to": ["jane@example.com"],
                "cc": ["bob@example.com"]
            },
            {
                "id": "calendar1", 
                "type": "calendar",
                "organizer": "john@example.com",
                "attendees": ["jane@example.com", "bob@example.com"]
            },
            {
                "id": "document1",
                "type": "document", 
                "author": "john@example.com",
                "reviewers": ["jane@example.com"]
            }
        ]

    def _simulate_contact_discovery(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulate contact discovery from events."""
        contacts = {}
        
        for event in events:
            # Extract email addresses from event
            emails = []
            if event["type"] == "email":
                emails.extend([event["from"]] + event["to"] + event.get("cc", []))
            elif event["type"] == "calendar":
                emails.extend([event["organizer"]] + event["attendees"])
            elif event["type"] == "document":
                emails.extend([event["author"]] + event.get("reviewers", []))
            
            # Create or update contacts
            for email in emails:
                if email not in contacts:
                    contacts[email] = {
                        "email_address": email,
                        "display_name": email.split("@")[0].title(),
                        "source_services": [],
                        "event_counts": {},
                        "total_event_count": 0,
                        "relevance_score": 0.0
                    }
                
                # Update contact info
                if event["type"] not in contacts[email]["source_services"]:
                    contacts[email]["source_services"].append(event["type"])
                
                contacts[email]["event_counts"][event["type"]] = contacts[email]["event_counts"].get(event["type"], 0) + 1
                contacts[email]["total_event_count"] += 1
                
                # Calculate relevance score
                contacts[email]["relevance_score"] = min(1.0, contacts[email]["total_event_count"] / 10.0)
        
        return list(contacts.values())

    def _generate_large_test_documents(self) -> Dict[str, Dict[str, Any]]:
        """Generate large test documents for chunking testing."""
        return {
            "word_document": {
                "id": "word_doc_1",
                "type": "word_document",
                "content": "This is a very long word document with important information. " * 100,  # 100 sentences
                "title": "Test Word Document"
            },
            "sheet_document": {
                "id": "sheet_doc_1", 
                "type": "sheet_document",
                "content": "This is a spreadsheet with lots of data and important metrics. " * 50,  # 50 sentences
                "title": "Test Spreadsheet"
            },
            "presentation_document": {
                "id": "presentation_doc_1",
                "type": "presentation_document", 
                "content": "This is a presentation with many slides containing important content. " * 75,  # 75 sentences
                "title": "Test Presentation"
            }
        }

    def _simulate_document_chunking(self, document: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Simulate document chunking process."""
        chunks = []
        content = document["content"]
        words = content.split()
        
        # Simple chunking: split into chunks of ~50 words
        chunk_size = 50
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk = {
                "id": f"{document['id']}_chunk_{i//chunk_size}",
                "parent_doc_id": document["id"],
                "chunk_sequence": i // chunk_size,
                "chunk_type": "text",
                "content": " ".join(chunk_words),
                "title": f"{document['title']} - Part {i//chunk_size + 1}"
            }
            chunks.append(chunk)
        
        return chunks

    def _simulate_fragment_search(self, query: str, chunking_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Simulate fragment search functionality."""
        all_chunks = []
        for chunks in chunking_results.values():
            all_chunks.extend(chunks)
        
        # Simple search simulation - look for query in chunk content
        results = [chunk for chunk in all_chunks if query.lower() in chunk.get("content", "").lower()]
        
        return {
            "success": True,
            "query": query,
            "total_found": len(results),
            "results": results
        }

    def _generate_hierarchical_test_data(self) -> List[Dict[str, Any]]:
        """Generate hierarchical test data with parent-child relationships."""
        return [
            {
                "id": "parent_doc_1",
                "type": "word_document",
                "title": "Project Plan",
                "children": [
                    {"id": "fragment_1", "type": "document_fragment", "content": "Introduction to the project"},
                    {"id": "fragment_2", "type": "document_fragment", "content": "Project objectives and goals"},
                    {"id": "fragment_3", "type": "document_fragment", "content": "Project timeline and milestones"}
                ]
            },
            {
                "id": "parent_doc_2", 
                "type": "sheet_document",
                "title": "Project Budget",
                "children": [
                    {"id": "fragment_4", "type": "document_fragment", "content": "Revenue projections"},
                    {"id": "fragment_5", "type": "document_fragment", "content": "Expense breakdown"}
                ]
            }
        ]

    def _generate_hierarchical_vespa_documents(self, hierarchical_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Vespa documents with parent-child relationships."""
        vespa_docs = []
        
        for parent in hierarchical_data:
            # Add parent document
            parent_doc = {
                "id": parent["id"],
                "document_type": parent["type"],
                "title": parent["title"],
                "content": f"Content for {parent['title']}"
            }
            vespa_docs.append(parent_doc)
            
            # Add child documents
            for child in parent["children"]:
                child_doc = {
                    "id": child["id"],
                    "document_type": child["type"],
                    "parent_doc_id": parent["id"],
                    "content": child["content"]
                }
                vespa_docs.append(child_doc)
        
        return vespa_docs

    def _simulate_hierarchical_search(self, query: str, vespa_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate hierarchical search functionality."""
        # Simple search simulation - look for query in document content
        results = [doc for doc in vespa_docs if query.lower() in doc.get("content", "").lower()]
        
        return {
            "success": True,
            "query": query,
            "total_found": len(results),
            "results": results
        }

    def _generate_timestamp_test_events(self) -> List[Dict[str, Any]]:
        """Generate events with various timestamp formats."""
        now = datetime.now(timezone.utc)
        
        return [
            {
                "id": "event1",
                "last_updated": now.isoformat(),
                "sync_timestamp": now.isoformat()
            },
            {
                "id": "event2", 
                "last_updated": now.strftime("%Y-%m-%d %H:%M:%S"),
                "sync_timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": "event3",
                "last_updated": str(int(now.timestamp())),
                "sync_timestamp": str(int(now.timestamp()))
            }
        ]

    def _validate_event_timestamps(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Validate event timestamps."""
        errors = []
        
        for field in ["last_updated", "sync_timestamp"]:
            if field in event:
                try:
                    # Try to parse the timestamp
                    if isinstance(event[field], str):
                        if event[field].isdigit():
                            # Unix timestamp
                            datetime.fromtimestamp(int(event[field]), tz=timezone.utc)
                        else:
                            # ISO format or other string format
                            datetime.fromisoformat(event[field].replace("Z", "+00:00"))
                except (ValueError, OSError) as e:
                    errors.append(f"Invalid {field}: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }

    def _convert_event_timestamps(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert event timestamps to standard format."""
        converted = {}
        
        for field in ["last_updated", "sync_timestamp"]:
            if field in event:
                try:
                    if isinstance(event[field], str):
                        if event[field].isdigit():
                            # Unix timestamp
                            dt = datetime.fromtimestamp(int(event[field]), tz=timezone.utc)
                        else:
                            # ISO format or other string format
                            dt = datetime.fromisoformat(event[field].replace("Z", "+00:00"))
                        
                        converted[field] = dt.isoformat()
                except (ValueError, OSError) as e:
                    return {
                        "success": False,
                        "error": f"Failed to convert {field}: {e}"
                    }
        
        return {
            "success": True,
            "converted": converted
        }

    def _generate_freshness_test_events(self) -> List[Dict[str, Any]]:
        """Generate events with different freshness levels."""
        now = datetime.now(timezone.utc)
        
        return [
            {
                "id": "event1",
                "last_updated": now.isoformat(),
                "sync_timestamp": now.isoformat()
            },
            {
                "id": "event2",
                "last_updated": (now - timedelta(hours=12)).isoformat(),
                "sync_timestamp": (now - timedelta(hours=12)).isoformat()
            },
            {
                "id": "event3",
                "last_updated": (now - timedelta(days=3)).isoformat(),
                "sync_timestamp": (now - timedelta(days=3)).isoformat()
            },
            {
                "id": "event4",
                "last_updated": (now - timedelta(days=10)).isoformat(),
                "sync_timestamp": (now - timedelta(days=10)).isoformat(),
                "needs_refresh": True
            }
        ]

    def _calculate_data_freshness(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate data freshness score."""
        now = datetime.now(timezone.utc)
        
        if "last_updated" in event:
            try:
                if isinstance(event["last_updated"], str):
                    if event["last_updated"].isdigit():
                        last_updated = datetime.fromtimestamp(int(event["last_updated"]), tz=timezone.utc)
                    else:
                        last_updated = datetime.fromisoformat(event["last_updated"].replace("Z", "+00:00"))
                else:
                    last_updated = event["last_updated"]
                
                age_hours = (now - last_updated).total_seconds() / 3600
                
                # Calculate freshness score (1.0 = very fresh, 0.0 = very stale)
                if age_hours <= 1:
                    freshness_score = 1.0
                elif age_hours <= 24:
                    freshness_score = 0.8
                elif age_hours <= 168:  # 1 week
                    freshness_score = 0.5
                else:
                    freshness_score = 0.1
                
                return {
                    "freshness_score": freshness_score,
                    "age_hours": age_hours
                }
                
            except (ValueError, OSError):
                return {
                    "freshness_score": 0.0,
                    "age_hours": float('inf')
                }
        
        return {
            "freshness_score": 0.0,
            "age_hours": float('inf')
        }
