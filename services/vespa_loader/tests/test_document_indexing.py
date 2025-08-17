"""
Tests for document indexing operations to catch ID corruption and field mapping issues.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from vespa_loader.content_normalizer import ContentNormalizer
from vespa_loader.vespa_client import VespaClient
import json


class TestDocumentIndexing:
    """Test document indexing operations and ID handling."""
    
    @pytest.fixture
    def content_normalizer(self):
        """Create a content normalizer instance."""
        return ContentNormalizer()
    
    @pytest.fixture
    def vespa_client(self):
        """Create a mocked Vespa client."""
        client = VespaClient("http://localhost:8080")
        client.session = AsyncMock()
        return client
    
    @pytest.fixture
    def sample_email_data(self):
        """Sample email data that would be processed by the loader."""
        return {
            "id": "email_001",
            "user_id": "test@example.com",
            "subject": "Test Email Subject",
            "body": "This is the body of a test email for indexing.",
            "from": "sender@example.com",
            "to": ["test@example.com"],
            "date": "2024-01-01T00:00:00Z",
            "labels": ["inbox", "important"]
        }
    
    def test_content_normalization_preserves_doc_id(self, content_normalizer, sample_email_data):
        """Test that content normalization doesn't corrupt the doc_id field."""
        # Normalize the email content
        normalized = content_normalizer.normalize_email(sample_email_data)
        
        # The doc_id should remain exactly as provided
        assert "doc_id" in normalized
        assert normalized["doc_id"] == "email_001"
        
        # The doc_id should NOT be a Vespa ID format
        assert not normalized["doc_id"].startswith("id:briefly:briefly_document::")
    
    def test_document_structure_consistency(self, content_normalizer, sample_email_data):
        """Test that normalized documents have consistent structure."""
        normalized = content_normalizer.normalize_email(sample_email_data)
        
        # Required fields should be present
        required_fields = ["user_id", "doc_id", "title", "content", "search_text"]
        for field in required_fields:
            assert field in normalized, f"Missing required field: {field}"
        
        # Field types should be correct
        assert isinstance(normalized["user_id"], str)
        assert isinstance(normalized["doc_id"], str)
        assert isinstance(normalized["title"], str)
        assert isinstance(normalized["content"], str)
        assert isinstance(normalized["search_text"], str)
    
    async def test_indexing_preserves_original_doc_id(self, vespa_client, sample_email_data):
        """Test that indexing preserves the original doc_id without corruption."""
        # Mock successful indexing response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": f"id:briefly:briefly_document::{sample_email_data['id']}",
            "status": "success"
        })
        
        vespa_client.session.post.return_value.__aenter__.return_value = mock_response
        
        # Index the document
        result = await vespa_client.index_document({
            "user_id": sample_email_data["user_id"],
            "doc_id": sample_email_data["id"],
            "title": sample_email_data["subject"],
            "content": sample_email_data["body"],
            "search_text": f"{sample_email_data['subject']} {sample_email_data['body']}"
        })
        
        # Verify the result contains the correct ID
        assert result["status"] == "success"
        assert "id" in result
        
        # The returned ID should follow the correct Vespa format
        expected_id = f"id:briefly:briefly_document::{sample_email_data['id']}"
        assert result["id"] == expected_id
        
        # Verify no ID duplication occurred
        id_parts = result["id"].split("::")
        assert len(id_parts) == 3
        assert id_parts[0] == "id"
        assert id_parts[1] == "briefly"
        assert id_parts[2] == "briefly_document"
    
    async def test_batch_indexing_id_consistency(self, vespa_client):
        """Test that batch indexing maintains ID consistency across documents."""
        documents = [
            {
                "user_id": "batch@example.com",
                "doc_id": f"batch_{i:03d}",
                "title": f"Batch Title {i}",
                "content": f"Batch content {i}",
                "search_text": f"batch {i}"
            }
            for i in range(3)
        ]
        
        # Mock successful batch responses
        mock_responses = []
        for doc in documents:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "id": f"id:briefly:briefly_document::{doc['doc_id']}",
                "status": "success"
            })
            mock_responses.append(mock_response)
        
        # Mock the session to return different responses for each call
        vespa_client.session.post.side_effect = lambda *args, **kwargs: mock_responses.pop(0)
        
        # Perform batch indexing
        for doc in documents:
            result = await vespa_client.index_document(doc)
            assert result["status"] == "success"
            
            # Verify ID format
            expected_id = f"id:briefly:briefly_document::{doc['doc_id']}"
            assert result["id"] == expected_id
            
            # Check for ID corruption
            assert not result["id"].endswith(f"::{expected_id}")
    
    def test_field_mapping_consistency(self, content_normalizer):
        """Test that field mapping is consistent across different email types."""
        email_variants = [
            {
                "id": "email_plain",
                "user_id": "test@example.com",
                "subject": "Plain Email",
                "body": "Simple text body",
                "from": "sender@example.com",
                "to": ["test@example.com"]
            },
            {
                "id": "email_html",
                "user_id": "test@example.com",
                "subject": "HTML Email",
                "body": "<html><body><p>HTML content</p></body></html>",
                "from": "sender@example.com",
                "to": ["test@example.com"]
            },
            {
                "id": "email_attachments",
                "user_id": "test@example.com",
                "subject": "Email with Attachments",
                "body": "Email body with attachments",
                "from": "sender@example.com",
                "to": ["test@example.com"],
                "attachments": ["file1.pdf", "file2.doc"]
            }
        ]
        
        for email in email_variants:
            normalized = content_normalizer.normalize_email(email)
            
            # All variants should have the same structure
            assert "doc_id" in normalized
            assert "user_id" in normalized
            assert "title" in normalized
            assert "content" in normalized
            assert "search_text" in normalized
            
            # doc_id should always match the original id
            assert normalized["doc_id"] == email["id"]
            
            # No field should contain Vespa ID format
            for field_name, field_value in normalized.items():
                if isinstance(field_value, str):
                    assert not field_value.startswith("id:briefly:briefly_document::"), \
                        f"Field {field_name} contains Vespa ID format: {field_value}"
    
    async def test_indexing_error_handling(self, vespa_client, sample_email_data):
        """Test that indexing errors are properly handled without corrupting IDs."""
        # Mock indexing failure
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.text = AsyncMock(return_value="Bad Request")
        
        vespa_client.session.post.return_value.__aenter__.return_value = mock_response
        
        # Attempt to index should raise exception
        with pytest.raises(Exception) as exc_info:
            await vespa_client.index_document({
                "user_id": sample_email_data["user_id"],
                "doc_id": sample_email_data["id"],
                "title": sample_email_data["subject"],
                "content": sample_email_data["body"],
                "search_text": f"{sample_email_data['subject']} {sample_email_data['body']}"
            })
        
        # Error should be properly formatted
        assert "Indexing failed: 400" in str(exc_info.value)
    
    def test_doc_id_uniqueness_constraints(self, content_normalizer):
        """Test that doc_id values maintain uniqueness constraints."""
        emails = [
            {
                "id": "unique_001",
                "user_id": "user1@example.com",
                "subject": "First Email",
                "body": "Content 1"
            },
            {
                "id": "unique_002", 
                "user_id": "user1@example.com",
                "subject": "Second Email",
                "body": "Content 2"
            },
            {
                "id": "unique_001",  # Duplicate ID
                "user_id": "user2@example.com", 
                "subject": "Third Email",
                "body": "Content 3"
            }
        ]
        
        normalized_docs = []
        for email in emails:
            normalized = content_normalizer.normalize_email(email)
            normalized_docs.append(normalized)
        
        # Check that doc_ids are preserved exactly
        assert normalized_docs[0]["doc_id"] == "unique_001"
        assert normalized_docs[1]["doc_id"] == "unique_002"
        assert normalized_docs[2]["doc_id"] == "unique_001"  # Duplicate preserved
        
        # Verify no automatic ID modification occurred
        for doc in normalized_docs:
            assert doc["doc_id"] in ["unique_001", "unique_002"]
    
    @pytest.mark.asyncio
    async def test_vespa_id_generation_consistency(self, vespa_client):
        """Test that Vespa ID generation is consistent and follows the expected pattern."""
        test_cases = [
            {"doc_id": "simple", "expected": "id:briefly:briefly_document::simple"},
            {"doc_id": "with_underscores", "expected": "id:briefly:briefly_document::with_underscores"},
            {"doc_id": "with-dashes", "expected": "id:briefly:briefly_document::with-dashes"},
            {"doc_id": "with.dots", "expected": "id:briefly:briefly_document::with.dots"},
            {"doc_id": "123_numbers", "expected": "id:briefly:briefly_document::123_numbers"},
            {"doc_id": "UPPER_case", "expected": "id:briefly:briefly_document::UPPER_case"},
        ]
        
        for test_case in test_cases:
            # Mock successful response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "id": test_case["expected"],
                "status": "success"
            })
            
            vespa_client.session.post.return_value.__aenter__.return_value = mock_response
            
            # Test indexing
            result = await vespa_client.index_document({
                "user_id": "test@example.com",
                "doc_id": test_case["doc_id"],
                "title": "Test",
                "content": "Test content",
                "search_text": "test"
            })
            
            # Verify ID format
            assert result["id"] == test_case["expected"]
            
            # Verify no corruption
            id_parts = result["id"].split("::")
            assert len(id_parts) == 3
            assert id_parts[0] == "id"
            assert id_parts[1] == "briefly"
            assert id_parts[2] == "briefly_document"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
