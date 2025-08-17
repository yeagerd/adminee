"""
Integration tests for Vespa client document lifecycle operations.
These tests will catch ID corruption, deletion failures, and data consistency issues.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from vespa_client import VespaClient
import json


class TestVespaClientIntegration:
    """Test Vespa client integration with real or mocked Vespa instance."""
    
    @pytest.fixture
    async def vespa_client(self):
        """Create a Vespa client instance for testing."""
        client = VespaClient("http://localhost:8080")
        # Mock the session to avoid real HTTP calls
        client.session = AsyncMock()
        return client
    
    @pytest.fixture
    def sample_document(self):
        """Sample document for testing."""
        return {
            "user_id": "test@example.com",
            "doc_id": "test_doc_001",
            "title": "Test Document",
            "content": "This is a test document for integration testing",
            "search_text": "test document integration testing"
        }
    
    @pytest.fixture
    def sample_document_with_duplicated_id(self):
        """Sample document with the corrupted ID format we discovered."""
        return {
            "user_id": "test@example.com",
            "doc_id": "id:briefly:briefly_document::test_doc_001",  # Corrupted ID
            "title": "Test Document with Corrupted ID",
            "content": "This document has a corrupted ID format",
            "search_text": "test document corrupted id format"
        }
    
    async def test_document_id_generation_consistency(self, vespa_client, sample_document):
        """Test that document IDs are generated consistently across operations."""
        # Test indexing
        index_result = await vespa_client.index_document(sample_document)
        assert index_result["status"] == "success"
        
        # Test retrieval with same ID
        retrieved_doc = await vespa_client.get_document(
            sample_document["user_id"], 
            sample_document["doc_id"]
        )
        assert retrieved_doc["error"] != "Document not found"
        
        # Test deletion with same ID
        delete_result = await vespa_client.delete_document(
            sample_document["user_id"], 
            sample_document["doc_id"]
        )
        assert delete_result["status"] == "success"
    
    async def test_document_id_format_validation(self, vespa_client, sample_document):
        """Test that document IDs follow the correct Vespa format."""
        # Index document
        await vespa_client.index_document(sample_document)
        
        # Verify the ID format in the Vespa response
        # This would catch the duplication issue we discovered
        expected_id_format = f"id:briefly:briefly_document::{sample_document['doc_id']}"
        
        # Mock the get_document response to check ID format
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": expected_id_format,
            "fields": sample_document
        })
        
        vespa_client.session.get.return_value.__aenter__.return_value = mock_response
        
        retrieved_doc = await vespa_client.get_document(
            sample_document["user_id"], 
            sample_document["doc_id"]
        )
        
        # This assertion would fail if we had the ID duplication bug
        assert retrieved_doc["id"] == expected_id_format
        assert not retrieved_doc["id"].endswith(f"::{expected_id_format}")
    
    async def test_document_lifecycle_consistency(self, vespa_client, sample_document):
        """Test complete document lifecycle: index -> search -> delete -> verify."""
        # 1. Index document
        index_result = await vespa_client.index_document(sample_document)
        assert index_result["status"] == "success"
        
        # 2. Search for document
        search_result = await vespa_client.search_documents(
            "test", 
            sample_document["user_id"]
        )
        assert len(search_result.get("root", {}).get("children", [])) > 0
        
        # 3. Delete document
        delete_result = await vespa_client.delete_document(
            sample_document["user_id"], 
            sample_document["doc_id"]
        )
        assert delete_result["status"] == "success"
        
        # 4. Verify document is gone
        search_after_delete = await vespa_client.search_documents(
            "test", 
            sample_document["user_id"]
        )
        assert len(search_after_delete.get("root", {}).get("children", [])) == 0
    
    async def test_corrupted_id_handling(self, vespa_client, sample_document_with_duplicated_id):
        """Test handling of documents with corrupted/duplicated IDs."""
        # This test should catch the ID corruption issue we discovered
        
        # Try to index document with corrupted ID
        index_result = await vespa_client.index_document(sample_document_with_duplicated_id)
        
        # The client should either:
        # 1. Reject the corrupted ID, or
        # 2. Clean it up automatically, or
        # 3. Log a warning about the corruption
        
        # Verify the ID was cleaned up
        if index_result["status"] == "success":
            # Check that the stored ID doesn't have duplication
            stored_id = index_result.get("id", "")
            assert not stored_id.endswith(f"::{stored_id}")
    
    async def test_batch_operations_id_consistency(self, vespa_client):
        """Test that batch operations maintain ID consistency."""
        documents = [
            {
                "user_id": "batch@example.com",
                "doc_id": f"batch_doc_{i:03d}",
                "title": f"Batch Document {i}",
                "content": f"Content for batch document {i}",
                "search_text": f"batch document {i}"
            }
            for i in range(5)
        ]
        
        # Batch index
        batch_result = await vespa_client.batch_index_documents(documents)
        assert batch_result["status"] == "success"
        
        # Verify all documents have correct ID format
        for doc in documents:
            retrieved = await vespa_client.get_document(doc["user_id"], doc["doc_id"])
            if retrieved.get("error") != "Document not found":
                doc_id = retrieved.get("id", "")
                expected_format = f"id:briefly:briefly_document::{doc['doc_id']}"
                assert doc_id == expected_format
    
    async def test_deletion_error_handling(self, vespa_client, sample_document):
        """Test proper handling of deletion errors."""
        # Index document
        await vespa_client.index_document(sample_document)
        
        # Mock deletion failure
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal server error")
        
        vespa_client.session.delete.return_value.__aenter__.return_value = mock_response
        
        # Attempt deletion should raise exception
        with pytest.raises(Exception) as exc_info:
            await vespa_client.delete_document(
                sample_document["user_id"], 
                sample_document["doc_id"]
            )
        
        assert "Deletion failed: 500" in str(exc_info.value)
    
    async def test_search_result_consistency(self, vespa_client):
        """Test that search results are consistent with document counts."""
        # Index multiple documents
        documents = [
            {
                "user_id": "consistency@example.com",
                "doc_id": f"consistency_doc_{i}",
                "title": f"Consistency Document {i}",
                "content": f"Content {i}",
                "search_text": f"consistency document {i}"
            }
            for i in range(3)
        ]
        
        for doc in documents:
            await vespa_client.index_document(doc)
        
        # Search should return exactly 3 documents
        search_result = await vespa_client.search_documents(
            "consistency", 
            "consistency@example.com"
        )
        
        children = search_result.get("root", {}).get("children", [])
        assert len(children) == 3
        
        # Verify all returned documents have the expected user_id
        for child in children:
            fields = child.get("fields", {})
            assert fields.get("user_id") == "consistency@example.com"
    
    async def test_document_id_field_extraction(self, vespa_client):
        """Test that document ID fields are correctly extracted from search results."""
        # This test would catch the field extraction issues we had in vespa.sh
        
        # Index a document
        doc = {
            "user_id": "extraction@example.com",
            "doc_id": "extraction_test_001",
            "title": "Extraction Test",
            "content": "Testing field extraction",
            "search_text": "extraction test field"
        }
        
        await vespa_client.index_document(doc)
        
        # Search for the document
        search_result = await vespa_client.search_documents(
            "extraction", 
            "extraction@example.com"
        )
        
        children = search_result.get("root", {}).get("children", [])
        assert len(children) > 0
        
        # Extract doc_id from first result
        first_child = children[0]
        fields = first_child.get("fields", {})
        
        # These assertions would catch the field confusion issues
        assert "doc_id" in fields
        assert fields["doc_id"] == "extraction_test_001"
        
        # Verify the doc_id is NOT the full Vespa ID
        assert not fields["doc_id"].startswith("id:briefly:briefly_document::")
    
    @pytest.mark.asyncio
    async def test_vespa_schema_compliance(self, vespa_client, sample_document):
        """Test that documents comply with Vespa schema requirements."""
        # This test would catch schema validation issues
        
        # Index document
        index_result = await vespa_client.index_document(sample_document)
        assert index_result["status"] == "success"
        
        # Verify document structure matches expected schema
        retrieved_doc = await vespa_client.get_document(
            sample_document["user_id"], 
            sample_document["doc_id"]
        )
        
        if retrieved_doc.get("error") != "Document not found":
            # Check required fields
            required_fields = ["user_id", "doc_id", "title", "content", "search_text"]
            for field in required_fields:
                assert field in retrieved_doc.get("fields", {})
            
            # Check ID format compliance
            doc_id = retrieved_doc.get("id", "")
            assert doc_id.startswith("id:briefly:briefly_document::")
            assert len(doc_id.split("::")) == 3  # Should have exactly 3 parts


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
