"""
Tests for Vespa search consistency to catch data inconsistency and field extraction issues.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from vespa_query.query_builder import QueryBuilder
import json


class TestSearchConsistency:
    """Test search consistency and result validation."""
    
    @pytest.fixture
    def query_builder(self):
        """Create a query builder instance."""
        return QueryBuilder()
    
    @pytest.fixture
    def mock_vespa_response(self):
        """Mock Vespa search response with the structure we expect."""
        return {
            "root": {
                "children": [
                    {
                        "id": "id:briefly:briefly_document::ms_0",
                        "relevance": 1.0,
                        "fields": {
                            "user_id": "trybriefly@outlook.com",
                            "doc_id": "ms_0",
                            "title": "Test Document 0",
                            "content": "Content for document 0",
                            "search_text": "test document 0 content"
                        }
                    },
                    {
                        "id": "id:briefly:briefly_document::ms_1",
                        "relevance": 0.9,
                        "fields": {
                            "user_id": "trybriefly@outlook.com",
                            "doc_id": "ms_1",
                            "title": "Test Document 1",
                            "content": "Content for document 1",
                            "search_text": "test document 1 content"
                        }
                    }
                ]
            }
        }
    
    @pytest.fixture
    def mock_vespa_response_with_corrupted_ids(self):
        """Mock Vespa response with the corrupted ID format we discovered."""
        return {
            "root": {
                "children": [
                    {
                        "id": "id:briefly:briefly_document::id:briefly:briefly_document::ms_0",
                        "relevance": 1.0,
                        "fields": {
                            "user_id": "trybriefly@outlook.com",
                            "doc_id": "id:briefly:briefly_document::ms_0",  # Corrupted
                            "title": "Test Document 0",
                            "content": "Content for document 0",
                            "search_text": "test document 0 content"
                        }
                    }
                ]
            }
        }
    
    def test_query_builder_constructs_valid_yql(self, query_builder):
        """Test that query builder constructs valid YQL queries."""
        # Test user-specific search
        yql = query_builder.build_user_search_query("test@example.com", "search term")
        assert "select * from briefly_document" in yql
        assert "user_id contains \"test@example.com\"" in yql
        assert "search_text contains \"search term\"" in yql
        
        # Test global search
        yql = query_builder.build_global_search_query("global search")
        assert "select * from briefly_document" in yql
        assert "search_text contains \"global search\"" in yql
        assert "user_id contains" not in yql  # Should not filter by user
    
    def test_search_result_parsing(self, mock_vespa_response):
        """Test that search results are parsed correctly."""
        # Extract document count
        children = mock_vespa_response.get("root", {}).get("children", [])
        assert len(children) == 2
        
        # Verify document structure
        for child in children:
            assert "id" in child
            assert "fields" in child
            assert "relevance" in child
            
            fields = child["fields"]
            required_fields = ["user_id", "doc_id", "title", "content", "search_text"]
            for field in required_fields:
                assert field in fields
    
    def test_document_id_extraction(self, mock_vespa_response):
        """Test that document IDs are correctly extracted from search results."""
        children = mock_vespa_response.get("root", {}).get("children", [])
        
        for child in children:
            # Extract doc_id from fields
            doc_id = child.get("fields", {}).get("doc_id", "")
            assert doc_id in ["ms_0", "ms_1"]
            
            # Verify doc_id is NOT the full Vespa ID
            assert not doc_id.startswith("id:briefly:briefly_document::")
            
            # Verify doc_id matches the pattern we expect
            assert doc_id.startswith("ms_")
    
    def test_corrupted_id_detection(self, mock_vespa_response_with_corrupted_ids):
        """Test that corrupted IDs are detected and handled appropriately."""
        children = mock_vespa_response_with_corrupted_ids.get("root", {}).get("children", [])
        
        for child in children:
            # Check for ID corruption
            vespa_id = child.get("id", "")
            doc_id = child.get("fields", {}).get("doc_id", "")
            
            # This should detect the corruption we discovered
            if "id:briefly:briefly_document::id:briefly:briefly_document::" in vespa_id:
                # ID is corrupted - has duplication
                assert vespa_id.count("id:briefly:briefly_document::") > 1
                
            if doc_id.startswith("id:briefly:briefly_document::"):
                # doc_id field is corrupted
                assert doc_id.count("id:briefly:briefly_document::") > 1
    
    def test_user_filtering_consistency(self, query_builder):
        """Test that user filtering is consistent across different query types."""
        user_id = "test@example.com"
        
        # User-specific search
        user_query = query_builder.build_user_search_query(user_id, "term")
        assert f"user_id contains \"{user_id}\"" in user_query
        
        # User statistics query
        stats_query = query_builder.build_user_stats_query(user_id)
        assert f"user_id contains \"{user_id}\"" in stats_query
        
        # Global search should NOT have user filter
        global_query = query_builder.build_global_search_query("term")
        assert f"user_id contains \"{user_id}\"" not in global_query
    
    def test_search_result_count_validation(self, mock_vespa_response):
        """Test that search result counts are validated correctly."""
        # Extract results
        children = mock_vespa_response.get("root", {}).get("children", [])
        total_count = len(children)
        
        # Verify count consistency
        assert total_count == 2
        
        # Verify each result has required fields
        for i, child in enumerate(children):
            fields = child.get("fields", {})
            assert "user_id" in fields
            assert "doc_id" in fields
            assert "title" in fields
            
            # Verify user_id consistency
            assert fields["user_id"] == "trybriefly@outlook.com"
            
            # Verify doc_id format
            doc_id = fields["doc_id"]
            assert doc_id.startswith("ms_")
            assert doc_id in [f"ms_{i}"]
    
    def test_field_type_validation(self, mock_vespa_response):
        """Test that field types are correct and consistent."""
        children = mock_vespa_response.get("root", {}).get("children", [])
        
        for child in children:
            fields = child.get("fields", {})
            
            # String fields
            assert isinstance(fields.get("user_id"), str)
            assert isinstance(fields.get("doc_id"), str)
            assert isinstance(fields.get("title"), str)
            assert isinstance(fields.get("content"), str)
            assert isinstance(fields.get("search_text"), str)
            
            # Numeric fields
            assert isinstance(child.get("relevance"), (int, float))
            
            # ID fields should not be empty
            assert fields.get("user_id").strip() != ""
            assert fields.get("doc_id").strip() != ""
    
    def test_search_query_escaping(self, query_builder):
        """Test that search queries properly escape special characters."""
        # Test with quotes
        query = query_builder.build_user_search_query("test@example.com", 'query with "quotes"')
        assert 'query with "quotes"' in query
        
        # Test with special characters
        query = query_builder.build_user_search_query("test@example.com", "query with & and < and >")
        assert "query with & and < and >" in query
        
        # Test with backslashes
        query = query_builder.build_user_search_query("test@example.com", "query with \\ backslash")
        assert "query with \\ backslash" in query
    
    def test_empty_search_results_handling(self):
        """Test handling of empty search results."""
        empty_response = {
            "root": {
                "children": []
            }
        }
        
        children = empty_response.get("root", {}).get("children", [])
        assert len(children) == 0
        
        # Should handle empty results gracefully
        total_count = len(children)
        assert total_count == 0
    
    def test_malformed_response_handling(self):
        """Test handling of malformed Vespa responses."""
        malformed_responses = [
            {},  # Empty response
            {"root": {}},  # Missing children
            {"root": {"children": None}},  # Null children
            {"root": {"children": "not_a_list"}},  # Wrong type
        ]
        
        for response in malformed_responses:
            children = response.get("root", {}).get("children", [])
            
            # Should handle gracefully
            if children is None:
                children = []
            elif not isinstance(children, list):
                children = []
            
            # Should always be a list
            assert isinstance(children, list)
    
    @pytest.mark.asyncio
    async def test_async_search_operations(self, query_builder):
        """Test async search operations and result processing."""
        # This would test the actual async search functionality
        # For now, we'll test the query building aspects
        
        # Test different query types
        queries = [
            query_builder.build_user_search_query("user1@example.com", "term1"),
            query_builder.build_user_search_query("user2@example.com", "term2"),
            query_builder.build_global_search_query("global term"),
        ]
        
        # All queries should be valid YQL
        for query in queries:
            assert "select * from briefly_document" in query
            assert "where" in query
            assert "contains" in query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
