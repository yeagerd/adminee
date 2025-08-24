"""
Tests for the document chunking service.
"""

import pytest

from services.vespa_loader.models.document_chunking import (
    ChunkingStrategy,
    ChunkType,
    DocumentChunkingConfig,
)
from services.vespa_loader.services.document_chunking_service import (
    DocumentChunkingService,
)


class TestDocumentChunkingService:
    """Test cases for DocumentChunkingService."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        from services.vespa_loader.models.document_chunking import (
            ChunkingRule,
            ChunkingStrategy,
        )

        # Create more lenient rules for testing
        return DocumentChunkingConfig(
            word_document_rules=ChunkingRule(
                name="test_word_document",
                strategy=ChunkingStrategy.HYBRID,
                min_chunk_size=50,  # Lower minimum
                max_chunk_size=2000,
                target_chunk_size=1000,
                overlap_size=100,
                preserve_sections=True,
                preserve_paragraphs=True,
                preserve_sentences=False,
                handle_tables=True,
                handle_lists=True,
                handle_images=True,
                min_content_quality=0.3,  # Lower quality threshold for tests
                max_empty_chunks=0,
                max_processing_time=60,
                batch_size=50,
            ),
            sheet_document_rules=ChunkingRule(
                name="test_sheet_document",
                strategy=ChunkingStrategy.SECTION_BOUNDARIES,
                min_chunk_size=30,  # Lower minimum
                max_chunk_size=1500,
                target_chunk_size=800,
                overlap_size=50,
                preserve_sections=True,
                preserve_paragraphs=False,
                preserve_sentences=False,
                handle_tables=True,
                handle_lists=False,
                handle_images=False,
                min_content_quality=0.3,  # Lower quality threshold for tests
                max_empty_chunks=1,
                max_processing_time=45,
                batch_size=100,
            ),
            presentation_document_rules=ChunkingRule(
                name="test_presentation_document",
                strategy=ChunkingStrategy.PAGE_LIMITS,
                min_chunk_size=40,  # Lower minimum
                max_chunk_size=1800,
                target_chunk_size=900,
                overlap_size=75,
                preserve_sections=True,
                preserve_paragraphs=True,
                preserve_sentences=False,
                handle_tables=True,
                handle_lists=True,
                handle_images=True,
                min_content_quality=0.3,  # Lower quality threshold for tests
                max_empty_chunks=0,
                max_processing_time=30,
                batch_size=75,
            ),
        )

    @pytest.fixture
    def service(self, config):
        """Create a DocumentChunkingService instance."""
        return DocumentChunkingService(config)

    @pytest.fixture
    def sample_word_document(self):
        """Create a sample Word document content."""
        return """
# Introduction

This is the introduction section of the document. It contains an overview and context.

## Background

The background section provides context and explains why this topic is important.

### Key Concepts

Here we introduce the key concepts that will be discussed. These form our base.

## Methodology

Our methodology involves several steps:

1. Data collection from multiple sources
2. Analysis using statistical methods
3. Validation through peer review
4. Documentation of findings

## Results

The results section presents our findings in detail. We found significant correlations.

### Statistical Analysis

Our statistical analysis revealed several patterns. The data shows clear trends.

## Conclusion

In conclusion, our research has provided valuable insights. We recommend further study.

## References

1. Smith, J. (2023). "Research Methods in Practice"
2. Johnson, A. (2022). "Statistical Analysis Handbook"
        """

    @pytest.fixture
    def sample_sheet_document(self):
        """Create a sample spreadsheet document content."""
        return """
Sheet 1: Sales Data

Product Name    | Q1 Sales | Q2 Sales | Q3 Sales | Q4 Sales
Product A       | 100      | 150      | 200      | 250
Product B       | 75       | 125      | 175      | 225
Product C       | 50       | 100      | 150      | 200

Sheet 2: Customer Analysis

Customer ID | Customer Name | Region    | Total Purchases
C001        | ABC Corp      | North     | $15,000
C002        | XYZ Inc       | South     | $22,500
C003        | DEF Ltd       | East      | $18,750

Sheet 3: Financial Summary

Revenue      | $500,000
Expenses     | $350,000
Profit       | $150,000
Margin       | 30%
        """

    @pytest.fixture
    def sample_presentation_document(self):
        """Create a sample presentation document content."""
        return """
Page 1: Title Slide

Project Overview
Presented by: Team Lead
Date: January 2024

---

Page 2: Agenda

• Introduction
• Project Goals
• Timeline
• Budget
• Next Steps

---

Page 3: Project Goals

Our primary objectives are:
1. Increase efficiency by 25%
2. Reduce costs by 15%
3. Improve customer satisfaction
4. Complete implementation by Q3

---

Page 4: Timeline

Phase 1: Planning (Jan-Feb)
Phase 2: Development (Mar-May)
Phase 3: Testing (Jun)
Phase 4: Deployment (Jul)

---

Page 5: Budget

Development: $100,000
Testing: $25,000
Deployment: $15,000
Total: $140,000

---

Page 6: Next Steps

• Finalize requirements
• Begin development
• Set up testing environment
• Prepare deployment plan
        """

    def test_hybrid_chunking_word_document(self, service, sample_word_document):
        """Test hybrid chunking for Word documents."""
        result = service.chunk_document(
            document_id="doc123",
            content=sample_word_document,
            document_type="word",
            metadata={"document_id": "doc123", "title": "Test Document"},
        )

        assert result.total_chunks > 0
        assert result.chunking_strategy == ChunkingStrategy.HYBRID
        assert result.chunking_rules.strategy == ChunkingStrategy.HYBRID

        # Check that chunks are properly sequenced
        assert result.validate_chunk_sequence()

        # Check chunk properties
        for chunk in result.chunks:
            assert chunk.parent_doc_id == "doc123"
            assert chunk.chunk_type in [ChunkType.SECTION, ChunkType.MIXED]
            assert chunk.content_length > 0
            assert chunk.word_count > 0
            assert chunk.search_text
            assert chunk.keywords

    def test_section_boundary_chunking_sheet_document(
        self, service, sample_sheet_document
    ):
        """Test section boundary chunking for spreadsheet documents."""
        result = service.chunk_document(
            document_id="sheet123",
            content=sample_sheet_document,
            document_type="sheet",
            metadata={"document_id": "sheet123", "title": "Sales Data"},
        )

        assert result.total_chunks > 0
        assert result.chunking_strategy == ChunkingStrategy.SECTION_BOUNDARIES

        # Check chunk properties
        for chunk in result.chunks:
            assert chunk.chunk_type == ChunkType.SECTION
            assert "Sheet" in chunk.title or chunk.title == "Introduction"

    def test_page_limit_chunking_presentation(
        self, service, sample_presentation_document
    ):
        """Test page limit chunking for presentation documents."""
        result = service.chunk_document(
            document_id="ppt123",
            content=sample_presentation_document,
            document_type="presentation",
            metadata={"document_id": "ppt123", "title": "Project Overview"},
        )

        assert result.total_chunks > 0
        assert result.chunking_strategy == ChunkingStrategy.PAGE_LIMITS

        # Check chunk properties
        for chunk in result.chunks:
            assert chunk.chunk_type == ChunkType.PAGE
            assert "Page" in chunk.title

    def test_fixed_size_chunking(self, service):
        """Test fixed-size chunking."""
        # Create a long document without clear structure
        long_content = "This is a very long document. " * 100

        result = service.chunk_document(
            document_id="long123",
            content=long_content,
            document_type="text",
            metadata={"document_id": "long123"},
        )

        assert result.total_chunks > 0

        # Check that chunks are roughly the same size
        chunk_sizes = [chunk.content_length for chunk in result.chunks]
        avg_size = sum(chunk_sizes) / len(chunk_sizes)

        for size in chunk_sizes:
            # Allow some variance but chunks should be reasonably consistent
            assert 0.5 * avg_size <= size <= 1.5 * avg_size

    def test_chunk_quality_scoring(self, service, sample_word_document):
        """Test that chunk quality scoring works correctly."""
        result = service.chunk_document(
            document_id="quality123", content=sample_word_document, document_type="word"
        )

        # Check quality metrics
        assert result.chunk_quality_score > 0.0
        assert result.chunk_quality_score <= 1.0
        assert result.content_coverage > 0.0
        assert result.empty_chunks == 0

        # Check individual chunk quality
        for chunk in result.chunks:
            quality = service._calculate_chunk_quality(chunk)
            assert 0.0 <= quality <= 1.0

    def test_chunk_metadata_and_relationships(self, service, sample_word_document):
        """Test that chunk metadata and relationships are properly set."""
        result = service.chunk_document(
            document_id="meta123", content=sample_word_document, document_type="word"
        )

        # Check that chunks have proper relationships
        for i, chunk in enumerate(result.chunks):
            if i > 0:
                assert chunk.previous_chunk_id == result.chunks[i - 1].id
            if i < len(result.chunks) - 1:
                assert chunk.next_chunk_id == result.chunks[i + 1].id

        # Check section paths
        for chunk in result.chunks:
            if chunk.title and chunk.title != "Introduction":
                assert chunk.title in chunk.section_path

    def test_content_cleaning_and_optimization(self, service):
        """Test that content is properly cleaned and optimized for search."""
        dirty_content = """
        This   is   a   document   with   excessive   whitespace.
        
        It also has
        - list markers
        - that should be removed
        
        And some special characters: @#$%^&*()
        """

        result = service.chunk_document(
            document_id="clean123", content=dirty_content, document_type="text"
        )

        # Check that content is cleaned
        for chunk in result.chunks:
            # Should not have excessive whitespace
            assert "   " not in chunk.content
            # Should not have list markers at start
            assert not chunk.content.startswith("- ")
            # Should have search-optimized text
            assert chunk.search_text
            assert len(chunk.search_text.split()) > 0

    def test_keyword_extraction(self, service):
        """Test that keywords are properly extracted from content."""
        content = """
        This document discusses machine learning algorithms and their applications.
        We focus on neural networks, deep learning, and artificial intelligence.
        The research shows significant improvements in accuracy and performance.
        """

        result = service.chunk_document(
            document_id="keywords123", content=content, document_type="text"
        )

        # Check that keywords are extracted
        for chunk in result.chunks:
            assert chunk.keywords
            # Should contain relevant terms
            relevant_terms = [
                "machine",
                "learning",
                "algorithms",
                "neural",
                "networks",
                "deep",
                "artificial",
                "intelligence",
            ]
            found_terms = [
                term
                for term in relevant_terms
                if any(term in keyword.lower() for keyword in chunk.keywords)
            ]
            assert len(found_terms) > 0

    def test_chunk_caching(self, service, sample_word_document):
        """Test that chunks are properly cached."""
        # First chunking
        result1 = service.chunk_document(
            document_id="cache123", content=sample_word_document, document_type="word"
        )

        # Check cache
        cached_chunks = service.get_cached_chunks("cache123")
        assert cached_chunks is not None
        assert len(cached_chunks) == result1.total_chunks

        # Second chunking should use cache
        result2 = service.chunk_document(
            document_id="cache123", content=sample_word_document, document_type="word"
        )

        # Results should be the same
        assert result1.total_chunks == result2.total_chunks

        # Check cache stats
        cache_stats = service.get_cache_stats()
        assert cache_stats["cached_documents"] > 0
        assert cache_stats["total_chunks"] > 0

    def test_chunk_validation(self, service, sample_word_document):
        """Test that chunk validation works correctly."""
        result = service.chunk_document(
            document_id="valid123", content=sample_word_document, document_type="word"
        )

        # Validation should pass
        assert result.validate_chunk_sequence()

        # Check sequence numbers
        sequences = [chunk.chunk_sequence for chunk in result.chunks]
        assert sequences == list(range(1, len(sequences) + 1))

        # Check for gaps
        for i in range(len(sequences) - 1):
            assert sequences[i + 1] - sequences[i] == 1

    def test_different_document_types(self, service):
        """Test chunking with different document types."""
        content = "This is a test document with some content."

        # Test Word document
        word_result = service.chunk_document("word123", content, "word")
        assert word_result.chunking_rules.strategy == ChunkingStrategy.HYBRID

        # Test spreadsheet
        sheet_result = service.chunk_document("sheet123", content, "sheet")
        assert (
            sheet_result.chunking_rules.strategy == ChunkingStrategy.SECTION_BOUNDARIES
        )

        # Test presentation
        ppt_result = service.chunk_document("ppt123", content, "presentation")
        assert ppt_result.chunking_rules.strategy == ChunkingStrategy.PAGE_LIMITS

        # Test unknown type (should use default)
        unknown_result = service.chunk_document("unknown123", content, "unknown")
        assert unknown_result.chunking_rules.strategy == ChunkingStrategy.HYBRID

    def test_error_handling(self, service):
        """Test error handling for invalid inputs."""
        # Test with None content
        with pytest.raises((TypeError, AttributeError)):
            service.chunk_document("none123", None, "word")

        # Test with empty content should handle gracefully
        result = service.chunk_document("empty123", "", "word")
        assert result.total_chunks == 0

        # Test with very short content
        short_content = "Hi"
        result = service.chunk_document("short123", short_content, "word")
        # Should handle gracefully, possibly with no chunks
        assert result.total_chunks >= 0

    def test_performance_metrics(self, service, sample_word_document):
        """Test that performance metrics are captured."""
        result = service.chunk_document(
            document_id="perf123", content=sample_word_document, document_type="word"
        )

        # Check performance metrics
        assert result.processing_time_seconds > 0
        assert result.memory_usage_mb >= 0

        # Check statistics
        assert result.total_chunks > 0
        assert result.total_content_length > 0
        assert result.average_chunk_size > 0
        assert result.chunk_size_variance >= 0
