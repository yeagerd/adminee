"""
Tests for the ingest service to prevent field mapping regressions.

This module tests the ingest_document_service function to ensure that
field mappings from VespaDocumentType.to_dict() are correctly handled.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.common.http_errors import ValidationError
from services.vespa_loader.content_normalizer import ContentNormalizer
from services.vespa_loader.embeddings import EmbeddingGenerator
from services.vespa_loader.ingest_service import ingest_document_service
from services.vespa_loader.vespa_client import VespaClient
from services.vespa_loader.vespa_types import VespaDocumentType


class TestIngestService:
    """Test the ingest_document_service function"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_vespa_client = MagicMock(spec=VespaClient)
        self.mock_content_normalizer = MagicMock(spec=ContentNormalizer)
        self.mock_embedding_generator = MagicMock(spec=EmbeddingGenerator)

        # Mock the Vespa client's index_document method
        self.mock_vespa_client.index_document = AsyncMock(
            return_value={"status": "success"}
        )

        # Mock the content normalizer
        self.mock_content_normalizer.normalize.return_value = "normalized content"

        # Mock the embedding generator
        self.mock_embedding_generator.generate_embedding = AsyncMock(
            return_value=[0.1, 0.2, 0.3]
        )

    def test_document_field_mapping_correctly_handled(self):
        """Test that the service correctly handles field mappings from to_dict()"""
        # Create a test document
        test_document = VespaDocumentType(
            id="test_doc_001",
            user_id="test_user_123",
            type="email",
            provider="gmail",
            subject="Test Subject",
            body="This is test content that should be normalized and embedded",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
            thread_id="thread_001",
            folder="inbox",
            metadata={"test": "metadata"},
        )

        # Convert to dict to simulate the actual flow
        vespa_document = test_document.to_dict()

        # Verify the field mapping happened correctly
        assert "body" not in vespa_document
        assert "content" in vespa_document
        assert (
            vespa_document["content"]
            == "This is test content that should be normalized and embedded"
        )

        # Verify other field mappings
        assert vespa_document["doc_id"] == "test_doc_001"
        assert vespa_document["title"] == "Test Subject"
        assert vespa_document["sender"] == "sender@test.com"
        assert vespa_document["recipients"] == ["recipient@test.com"]

    @pytest.mark.asyncio
    async def test_content_normalization_uses_correct_field(self):
        """Test that content normalization accesses the 'content' field, not 'body'"""
        test_document = VespaDocumentType(
            id="test_doc_001",
            user_id="test_user_123",
            type="email",
            provider="gmail",
            subject="Test Subject",
            body="Original content",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
        )

        # Run the service
        result = await ingest_document_service(
            test_document,
            self.mock_vespa_client,
            self.mock_content_normalizer,
            self.mock_embedding_generator,
        )

        # Verify the content normalizer was called with the correct content
        self.mock_content_normalizer.normalize.assert_called_once_with(
            "Original content"
        )

        # Verify the result
        assert result.status == "success"
        assert result.document_id == "test_doc_001"

    @pytest.mark.asyncio
    async def test_embedding_generation_uses_correct_field(self):
        """Test that embedding generation accesses the 'content' field, not 'body'"""
        test_document = VespaDocumentType(
            id="test_doc_001",
            user_id="test_user_123",
            type="email",
            provider="gmail",
            subject="Test Subject",
            body="Content for embedding",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
        )

        # Run the service
        result = await ingest_document_service(
            test_document,
            self.mock_vespa_client,
            self.mock_content_normalizer,
            self.mock_embedding_generator,
        )

        # Verify the embedding generator was called with the normalized content
        # (since normalization happens before embedding generation)
        self.mock_embedding_generator.generate_embedding.assert_called_once_with(
            "normalized content"
        )

        # Verify the result
        assert result.status == "success"
        assert result.document_id == "test_doc_001"

    @pytest.mark.asyncio
    async def test_service_without_content_normalizer(self):
        """Test that the service works correctly without a content normalizer"""
        test_document = VespaDocumentType(
            id="test_doc_001",
            user_id="test_user_123",
            type="email",
            provider="gmail",
            subject="Test Subject",
            body="Test content",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
        )

        # Run the service without content normalizer
        result = await ingest_document_service(
            test_document,
            self.mock_vespa_client,
            None,  # No content normalizer
            self.mock_embedding_generator,
        )

        # Verify content normalizer was not called
        self.mock_content_normalizer.normalize.assert_not_called()

        # Verify the result
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_service_without_embedding_generator(self):
        """Test that the service works correctly without an embedding generator"""
        test_document = VespaDocumentType(
            id="test_doc_001",
            user_id="test_user_123",
            type="email",
            provider="gmail",
            subject="Test Subject",
            body="Test content",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
        )

        # Run the service without embedding generator
        result = await ingest_document_service(
            test_document,
            self.mock_vespa_client,
            self.mock_content_normalizer,
            None,  # No embedding generator
        )

        # Verify embedding generator was not called
        self.mock_embedding_generator.generate_embedding.assert_not_called()

        # Verify the result
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_validation_error_missing_id(self):
        """Test that validation error is raised for missing document ID"""
        test_document = VespaDocumentType(
            id="",  # Empty ID
            user_id="test_user_123",
            type="email",
            provider="gmail",
            subject="Test Subject",
            body="Test content",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
        )

        with pytest.raises(ValidationError) as exc_info:
            await ingest_document_service(
                test_document,
                self.mock_vespa_client,
                self.mock_content_normalizer,
                self.mock_embedding_generator,
            )

        assert "Document ID and user_id are required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_error_missing_user_id(self):
        """Test that validation error is raised for missing user ID"""
        test_document = VespaDocumentType(
            id="test_doc_001",
            user_id="",  # Empty user ID
            type="email",
            provider="gmail",
            subject="Test Subject",
            body="Test content",
            from_address="sender@test.com",
            to_addresses=["recipient@test.com"],
        )

        with pytest.raises(ValidationError) as exc_info:
            await ingest_document_service(
                test_document,
                self.mock_vespa_client,
                self.mock_content_normalizer,
                self.mock_embedding_generator,
            )

        assert "Document ID and user_id are required" in str(exc_info.value)
