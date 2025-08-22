"""
Tests for DocumentMapper alias handling

This module tests the DocumentMapper's ability to handle field aliases
and align with VespaDocumentType field names.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from services.vespa_loader.mapper import DocumentMapper


class TestDocumentMapperAliasHandling:
    """Test DocumentMapper alias handling and field alignment"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mapper = DocumentMapper()
        self.test_user_id = "test_user_123"
        self.test_timestamp = datetime.now(timezone.utc)

    def test_email_field_aliases(self):
        """Test email field aliases (from_address↔from, to_addresses↔to)"""
        # Test with primary field names
        email_data_primary = {
            "user_id": self.test_user_id,
            "id": "email_001",
            "provider": "gmail",
            "subject": "Test Email",
            "body": "Test body",
            "from_address": "sender@example.com",
            "to_addresses": ["recipient@example.com"],
            "thread_id": "thread_001",
            "folder": "inbox",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc_primary = self.mapper.map_to_vespa(email_data_primary)
        
        # Test with alias field names
        email_data_alias = {
            "user_id": self.test_user_id,
            "id": "email_002",
            "provider": "gmail",
            "subject": "Test Email 2",
            "body": "Test body 2",
            "from": "sender2@example.com",  # Alias for from_address
            "to": ["recipient2@example.com"],  # Alias for to_addresses
            "thread_id": "thread_002",
            "folder": "sent",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc_alias = self.mapper.map_to_vespa(email_data_alias)
        
        # Verify both produce the same field structure
        assert vespa_doc_primary["from_address"] == "sender@example.com"
        assert vespa_doc_primary["to_addresses"] == ["recipient@example.com"]
        assert vespa_doc_alias["from_address"] == "sender2@example.com"
        assert vespa_doc_alias["to_addresses"] == ["recipient2@example.com"]
        
        # Verify field names align with VespaDocumentType
        assert "from_address" in vespa_doc_primary
        assert "to_addresses" in vespa_doc_primary
        assert "subject" in vespa_doc_primary
        assert "body" in vespa_doc_primary

    def test_calendar_field_aliases(self):
        """Test calendar field aliases"""
        # Test with primary field names
        calendar_data_primary = {
            "user_id": self.test_user_id,
            "id": "calendar_001",
            "provider": "google",
            "subject": "Test Meeting",
            "body": "Test meeting description",
            "from_address": "organizer@example.com",
            "to_addresses": ["attendee@example.com"],
            "start_time": self.test_timestamp,
            "end_time": self.test_timestamp,
            "location": "Room A",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc_primary = self.mapper.map_to_vespa(calendar_data_primary)
        
        # Test with alias field names
        calendar_data_alias = {
            "user_id": self.test_user_id,
            "id": "calendar_002",
            "provider": "google",
            "subject": "Test Meeting 2",
            "body": "Test meeting description 2",
            "from": "organizer2@example.com",  # Alias for from_address
            "to": ["attendee2@example.com"],  # Alias for to_addresses
            "start_time": self.test_timestamp,
            "end_time": self.test_timestamp,
            "location": "Room B",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc_alias = self.mapper.map_to_vespa(calendar_data_alias)
        
        # Verify both produce the same field structure
        assert vespa_doc_primary["from_address"] == "organizer@example.com"
        assert vespa_doc_primary["to_addresses"] == ["attendee@example.com"]
        assert vespa_doc_alias["from_address"] == "organizer2@example.com"
        assert vespa_doc_alias["to_addresses"] == ["attendee2@example.com"]

    def test_contact_field_mapping(self):
        """Test contact field mapping to VespaDocumentType structure"""
        contact_data = {
            "user_id": self.test_user_id,
            "id": "contact_001",
            "provider": "google",
            "display_name": "John Doe",  # Maps to subject
            "email_addresses": ["john@example.com"],  # Maps to to_addresses
            "phone_numbers": ["+1234567890"],
            "company": "Example Corp",
            "job_title": "Developer",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc = self.mapper.map_to_vespa(contact_data)
        
        # Verify field mapping
        assert vespa_doc["subject"] == "John Doe"  # display_name → subject
        assert vespa_doc["to_addresses"] == ["john@example.com"]  # email_addresses → to_addresses
        assert vespa_doc["from_address"] == ""  # Empty for contacts
        assert vespa_doc["type"] == "contact"

    def test_file_field_mapping(self):
        """Test file field mapping to VespaDocumentType structure"""
        file_data = {
            "user_id": self.test_user_id,
            "id": "file_001",
            "provider": "microsoft",
            "name": "Test Document.docx",  # Maps to subject
            "content": "This is test content",  # Maps to body
            "file_type": "docx",
            "size": 1024,
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc = self.mapper.map_to_vespa(file_data)
        
        # Verify field mapping
        assert vespa_doc["subject"] == "Test Document.docx"  # name → subject
        assert vespa_doc["body"] == "This is test content"  # content → body
        assert vespa_doc["type"] == "file"

    def test_field_alias_priority(self):
        """Test that primary field names take priority over aliases"""
        email_data = {
            "user_id": self.test_user_id,
            "id": "email_001",
            "provider": "gmail",
            "subject": "Test Email",
            "body": "Test body",
            "from_address": "primary@example.com",  # Primary field
            "from": "alias@example.com",  # Alias field
            "to_addresses": ["primary@example.com"],  # Primary field
            "to": ["alias@example.com"],  # Alias field
            "thread_id": "thread_001",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc = self.mapper.map_to_vespa(email_data)
        
        # Primary fields should take priority
        assert vespa_doc["from_address"] == "primary@example.com"
        assert vespa_doc["to_addresses"] == ["primary@example.com"]

    def test_missing_fields_handling(self):
        """Test handling of missing fields gracefully"""
        minimal_data = {
            "user_id": self.test_user_id,
            "id": "minimal_001",
            "provider": "test"
        }
        
        vespa_doc = self.mapper.map_to_vespa(minimal_data)
        
        # Should handle missing fields gracefully
        assert vespa_doc["id"] == "minimal_001"
        assert vespa_doc["user_id"] == self.test_user_id
        assert vespa_doc["subject"] == ""  # Default empty string
        assert vespa_doc["body"] == ""  # Default empty string
        assert vespa_doc["from_address"] == ""  # Default empty string
        assert vespa_doc["to_addresses"] == []  # Default empty list

    def test_field_type_consistency(self):
        """Test that field types are consistent with VespaDocumentType"""
        email_data = {
            "user_id": self.test_user_id,
            "id": "email_001",
            "provider": "gmail",
            "subject": "Test Email",
            "body": "Test body",
            "from_address": "sender@example.com",
            "to_addresses": ["recipient@example.com"],
            "thread_id": "thread_001",
            "folder": "inbox",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc = self.mapper.map_to_vespa(email_data)
        
        # Verify field types match VespaDocumentType expectations
        assert isinstance(vespa_doc["id"], str)
        assert isinstance(vespa_doc["user_id"], str)
        assert isinstance(vespa_doc["type"], str)
        assert isinstance(vespa_doc["provider"], str)
        assert isinstance(vespa_doc["subject"], str)
        assert isinstance(vespa_doc["body"], str)
        assert isinstance(vespa_doc["from_address"], str)
        assert isinstance(vespa_doc["to_addresses"], list)
        assert isinstance(vespa_doc["metadata"], dict)

    def test_search_text_generation_with_aliases(self):
        """Test search text generation works with both primary and alias fields"""
        # Test with primary fields
        email_data_primary = {
            "user_id": self.test_user_id,
            "id": "email_001",
            "provider": "gmail",
            "subject": "Test Email",
            "body": "Test body content",
            "from_address": "sender@example.com",
            "to_addresses": ["recipient@example.com"],
            "thread_id": "thread_001",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc_primary = self.mapper.map_to_vespa(email_data_primary)
        search_text_primary = vespa_doc_primary["search_text"]
        
        # Test with alias fields
        email_data_alias = {
            "user_id": self.test_user_id,
            "id": "email_002",
            "provider": "gmail",
            "subject": "Test Email 2",
            "body": "Test body content 2",
            "from": "sender2@example.com",
            "to": ["recipient2@example.com"],
            "thread_id": "thread_002",
            "created_at": self.test_timestamp,
            "updated_at": self.test_timestamp
        }
        
        vespa_doc_alias = self.mapper.map_to_vespa(email_data_alias)
        search_text_alias = vespa_doc_alias["search_text"]
        
        # Both should generate searchable text
        assert "Test Email" in search_text_primary
        assert "sender@example.com" in search_text_primary
        assert "recipient@example.com" in search_text_primary
        
        assert "Test Email 2" in search_text_alias
        assert "sender2@example.com" in search_text_alias
        assert "recipient2@example.com" in search_text_alias
