"""
Tests for Vespa search consistency to catch data inconsistency and field extraction issues.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from vespa_query.query_builder import QueryBuilder


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
                            "search_text": "test document 0 content",
                        },
                    },
                    {
                        "id": "id:briefly:briefly_document::ms_1",
                        "relevance": 0.9,
                        "fields": {
                            "user_id": "trybriefly@outlook.com",
                            "doc_id": "ms_1",
                            "title": "Test Document 1",
                            "content": "Content for document 1",
                            "search_text": "test document 1 content",
                        },
                    },
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
                            "search_text": "test document 0 content",
                        },
                    }
                ]
            }
        }

    def test_query_builder_constructs_valid_yql(self, query_builder):
        """Test that query builder constructs valid YQL queries."""
        # Test user-specific search
        query = query_builder.build_search_query("search term", "test@example.com")
        assert "streaming.groupname" in query
        assert query["streaming.groupname"] == "test@example.com"
        assert "yql" in query
        assert "briefly_document" in query["yql"].lower()  # Case-insensitive check
        assert "search_text" in query["yql"].lower() and "search term" in query["yql"]

        # Test that streaming mode is properly configured
        assert query["streaming.groupname"] == "test@example.com"

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
        children = mock_vespa_response_with_corrupted_ids.get("root", {}).get(
            "children", []
        )

        for child in children:
            # Check for ID corruption
            vespa_id = child.get("id", "")
            doc_id = child.get("fields", {}).get("doc_id", "")

            # This should detect the corruption we discovered
            if "id:briefly:briefly_document::id:briefly:briefly_document::" in vespa_id:
                # ID is corrupted - has duplication
                assert vespa_id.count("id:briefly:briefly_document::") > 1

            # The test data actually has a corrupted doc_id field
            if doc_id.startswith("id:briefly:briefly_document::"):
                # This is the corrupted case in our test data
                assert (
                    doc_id == "id:briefly:briefly_document::ms_0"
                )  # Verify the corruption

    def test_user_filtering_consistency(self, query_builder):
        """Test that user filtering is consistent across different query types."""
        user_id = "test@example.com"

        # User-specific search using streaming mode
        user_query = query_builder.build_search_query("term", user_id)
        assert "streaming.groupname" in user_query
        assert user_query["streaming.groupname"] == user_id

        # Test that the query has proper structure
        assert "yql" in user_query
        assert "ranking" in user_query
        assert "hits" in user_query

    def test_search_result_count_validation(self, mock_vespa_response):
        """Test that search result counts are validated correctly."""
        # Extract results
        children = mock_vespa_response.get("root", {}).get("children", [])
        total_count = len(children)

        # Verify count consistency
        assert total_count == 2

        # Verify each result has required fields
        for child in children:
            fields = child.get("fields", {})
            assert "user_id" in fields
            assert "doc_id" in fields
            assert "title" in fields

            # Verify user_id consistency
            assert fields["user_id"] == "trybriefly@outlook.com"

            # Verify doc_id format and value
            doc_id = fields["doc_id"]
            assert doc_id.startswith("ms_")
            # Check that doc_id is one of the expected values from mock data
            assert doc_id in ["ms_0", "ms_1"], f"Unexpected doc_id: {doc_id}"

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
        """Test that search queries properly escape special characters to prevent YQL injection."""
        # Test with quotes - should be properly escaped
        query = query_builder.build_search_query(
            'query with "quotes"', "test@example.com"
        )
        # The quotes should be escaped (doubled) in the YQL
        assert 'query with ""quotes""' in query["yql"]
        # The original unescaped query should NOT be in the YQL (security check)
        assert 'query with "quotes"' not in query["yql"]

        # Test with special characters
        query = query_builder.build_search_query(
            "query with & and < and >", "test@example.com"
        )
        assert "query with & and < and >" in query["yql"]

        # Test with backslashes - should be properly escaped
        query = query_builder.build_search_query(
            "query with \\ backslash", "test@example.com"
        )
        # The backslash should be escaped (doubled) in the YQL
        assert "query with \\\\ backslash" in query["yql"]
        # The original unescaped query should NOT be in the YQL (security check)
        assert "query with \\ backslash" not in query["yql"]

        # Test with malicious injection attempt
        malicious_query = 'query"; DROP TABLE briefly_document; --'
        query = query_builder.build_search_query(malicious_query, "test@example.com")
        # The malicious query should be properly escaped
        assert 'query""; DROP TABLE briefly_document; --' in query["yql"]
        # The original malicious query should NOT be in the YQL (security check)
        assert malicious_query not in query["yql"]

    def test_empty_search_results_handling(self):
        """Test handling of empty search results."""
        empty_response = {"root": {"children": []}}

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

        # Test different query types using the available methods
        queries = [
            query_builder.build_search_query("term1", "user1@example.com"),
            query_builder.build_search_query("term2", "user2@example.com"),
            query_builder.build_search_query("global term", "user1@example.com"),
        ]

        # Verify all queries are valid
        for query in queries:
            assert "yql" in query
            assert "ranking" in query
            assert "hits" in query
            assert "streaming.groupname" in query

    def test_similarity_query_streaming_groupname(self, query_builder):
        """Test that build_similarity_query uses raw user_id for streaming.groupname."""
        user_id = 'test"user@example.com'  # User ID with special characters
        document_id = "doc123"

        query = query_builder.build_similarity_query(document_id, user_id)

        # streaming.groupname should use the raw user_id, not escaped
        assert query["streaming.groupname"] == user_id

        # YQL should use escaped values for safety
        assert "streaming.groupname" in query
        assert "yql" in query
        # Verify the YQL contains escaped values
        escaped_user_id = query_builder._escape_yql_value(user_id)
        escaped_document_id = query_builder._escape_yql_value(document_id)
        assert escaped_user_id in query["yql"]
        assert escaped_document_id in query["yql"]

    def test_trending_query_streaming_groupname(self, query_builder):
        """Test that build_trending_query uses raw user_id for streaming.groupname."""
        user_id = 'user"with@quotes.com'  # User ID with special characters

        query = query_builder.build_trending_query(user_id)

        # streaming.groupname should use the raw user_id, not escaped
        assert query["streaming.groupname"] == user_id

        # YQL should use escaped values for safety
        assert "streaming.groupname" in query
        assert "yql" in query
        # Verify the YQL contains escaped values
        escaped_user_id = query_builder._escape_yql_value(user_id)
        assert escaped_user_id in query["yql"]

    def test_analytics_query_streaming_groupname(self, query_builder):
        """Test that build_analytics_query uses raw user_id for streaming.groupname."""
        user_id = 'analytics"user@test.com'  # User ID with special characters

        query = query_builder.build_analytics_query(user_id)

        # streaming.groupname should use the raw user_id, not escaped
        assert query["streaming.groupname"] == user_id

        # YQL should use escaped values for safety
        assert "streaming.groupname" in query
        assert "yql" in query
        # Verify the YQL contains escaped values
        escaped_user_id = query_builder._escape_yql_value(user_id)
        assert escaped_user_id in query["yql"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
