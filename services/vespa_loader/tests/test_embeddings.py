#!/usr/bin/env python3
"""
Tests for the EmbeddingGenerator
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

from services.vespa_loader.embeddings import EmbeddingGenerator


class TestEmbeddingGenerator:
    """Test the EmbeddingGenerator functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.test_model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.test_text = "This is a test sentence for embedding generation."
        self.test_texts = ["First text", "Second text", "Third text"]

    def test_initialization_with_default_model(self):
        """Test initialization with default model name"""
        with patch('builtins.__import__') as mock_import:
            # Mock the sentence_transformers import
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            assert generator.model_name == self.test_model_name
            assert generator.model == mock_model
            assert generator.is_model_loaded() is True
            mock_transformer_class.assert_called_once_with(self.test_model_name)

    def test_initialization_with_custom_model(self):
        """Test initialization with custom model name"""
        custom_model = "custom-model-name"
        with patch('builtins.__import__') as mock_import:
            # Mock the sentence_transformers import
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator(custom_model)
            
            assert generator.model_name == custom_model
            assert generator.model == mock_model
            mock_transformer_class.assert_called_once_with(custom_model)

    def test_initialization_failure(self):
        """Test initialization failure handling"""
        with patch('builtins.__import__') as mock_import:
            # Mock the import to fail specifically for sentence_transformers
            def mock_import_side_effect(name, *args, **kwargs):
                if 'sentence_transformers' in name:
                    raise ImportError("Module not found")
                return Mock()  # Return mock for other imports
            
            mock_import.side_effect = mock_import_side_effect
            
            with pytest.raises(RuntimeError, match="Failed to initialize embedding model"):
                EmbeddingGenerator()

    def test_get_embedding_dimension(self):
        """Test getting embedding dimension"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            assert generator.get_embedding_dimension() == 384

    def test_is_model_loaded(self):
        """Test model loaded status check"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            assert generator.is_model_loaded() is True

    def test_get_model_info(self):
        """Test getting model information"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            info = generator.get_model_info()
            
            assert info["model_name"] == self.test_model_name
            assert info["is_loaded"] is True
            assert info["dimension"] == 384
            assert info["type"] == "real"

    def test_preprocess_text_basic(self):
        """Test basic text preprocessing"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            # Test basic preprocessing
            result = generator.preprocess_text("  Test Text  ")
            assert result == "test text"
            
            # Test empty text
            result = generator.preprocess_text("")
            assert result == ""
            
            # Test None text
            result = generator.preprocess_text(None)
            assert result == ""

    def test_preprocess_text_truncation(self):
        """Test text truncation for long content"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            # Create text that will definitely exceed 512 chars after normalization
            # Use a pattern that won't be shortened by whitespace normalization
            # The truncation adds "..." so we need to ensure the result is <= 512
            long_text = "verylongwordwithoutspaces" * 30  # 30 * 25 = 750 characters
            
            result = generator.preprocess_text(long_text)
            
            # The result should be truncated to 512 chars + "..." = 515 total
            # But the actual truncation happens at 512, so result should be <= 515
            assert len(result) <= 515
            assert result.endswith("...")
            # Verify the actual content before "..." is <= 512
            content_before_ellipsis = result[:-3]  # Remove "..."
            assert len(content_before_ellipsis) <= 512

    def test_preprocess_text_whitespace_handling(self):
        """Test whitespace normalization"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            text = "  multiple    spaces\n\nand\nnewlines  "
            result = generator.preprocess_text(text)
            
            assert result == "multiple spaces and newlines"

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self):
        """Test successful embedding generation"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_embedding = np.array([0.1, 0.2, 0.3] + [0.0] * 381)  # 384 dimensions
            mock_model.encode.return_value = mock_embedding
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_embedding(self.test_text)
            
            assert len(result) == 384
            assert result[:3] == [0.1, 0.2, 0.3]
            mock_model.encode.assert_called_once_with(self.test_text)

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self):
        """Test embedding generation with empty text"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_embedding("")
            
            assert len(result) == 384
            assert all(val == 0.0 for val in result)

    @pytest.mark.asyncio
    async def test_generate_embedding_none_text(self):
        """Test embedding generation with None text"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_embedding(None)
            
            assert len(result) == 384
            assert all(val == 0.0 for val in result)

    @pytest.mark.asyncio
    async def test_generate_embedding_model_not_loaded(self):
        """Test embedding generation when model is not loaded"""
        # Create generator without calling __init__ to avoid model loading
        generator = EmbeddingGenerator.__new__(EmbeddingGenerator)
        generator.model = None
        generator.model_name = "test-model"
        
        # Should return zero vector when model is not loaded (due to error handling)
        result = await generator.generate_embedding(self.test_text)
        assert len(result) == 384
        assert all(val == 0.0 for val in result)

    @pytest.mark.asyncio
    async def test_generate_embedding_encoding_error(self):
        """Test embedding generation with encoding error"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_model.encode.side_effect = Exception("Encoding failed")
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_embedding(self.test_text)
            
            # Should return zero vector on error
            assert len(result) == 384
            assert all(val == 0.0 for val in result)

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_success(self):
        """Test successful batch embedding generation"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_embeddings = np.array([
                [0.1, 0.2, 0.3] + [0.0] * 381,
                [0.4, 0.5, 0.6] + [0.0] * 381,
                [0.7, 0.8, 0.9] + [0.0] * 381
            ])
            mock_model.encode.return_value = mock_embeddings
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_batch_embeddings(self.test_texts)
            
            assert len(result) == 3
            assert all(len(emb) == 384 for emb in result)
            mock_model.encode.assert_called_once_with(self.test_texts)

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_empty_list(self):
        """Test batch embedding generation with empty list"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_batch_embeddings([])
            
            assert result == []

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_model_not_loaded(self):
        """Test batch embedding generation when model is not loaded"""
        # Create generator without calling __init__ to avoid model loading
        generator = EmbeddingGenerator.__new__(EmbeddingGenerator)
        generator.model = None
        generator.model_name = "test-model"
        
        # Should return zero vectors when model is not loaded (due to error handling)
        result = await generator.generate_batch_embeddings(self.test_texts)
        assert len(result) == 3
        assert all(len(emb) == 384 for emb in result)
        assert all(all(val == 0.0 for val in emb) for emb in result)

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_encoding_error(self):
        """Test batch embedding generation with encoding error"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_model.encode.side_effect = Exception("Batch encoding failed")
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_batch_embeddings(self.test_texts)
            
            # Should return zero vectors on error
            assert len(result) == 3
            assert all(len(emb) == 384 for emb in result)
            assert all(all(val == 0.0 for val in emb) for emb in result)

    @pytest.mark.asyncio
    async def test_similarity_calculation(self):
        """Test cosine similarity calculation"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            # Test with identical embeddings
            embedding1 = [1.0, 0.0, 0.0] + [0.0] * 381
            embedding2 = [1.0, 0.0, 0.0] + [0.0] * 381
            
            similarity = await generator.similarity(embedding1, embedding2)
            assert similarity == 1.0
            
            # Test with orthogonal embeddings
            embedding1 = [1.0, 0.0, 0.0] + [0.0] * 381
            embedding2 = [0.0, 1.0, 0.0] + [0.0] * 381
            
            similarity = await generator.similarity(embedding1, embedding2)
            assert similarity == 0.0

    @pytest.mark.asyncio
    async def test_similarity_different_dimensions(self):
        """Test similarity calculation with different dimensions"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            embedding1 = [1.0, 0.0, 0.0]
            embedding2 = [1.0, 0.0, 0.0, 0.0]
            
            with pytest.raises(ValueError, match="Embeddings must have the same dimension"):
                await generator.similarity(embedding1, embedding2)

    @pytest.mark.asyncio
    async def test_similarity_zero_vectors(self):
        """Test similarity calculation with zero vectors"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            embedding1 = [0.0] * 384
            embedding2 = [0.0] * 384
            
            similarity = await generator.similarity(embedding1, embedding2)
            assert similarity == 0.0

    @pytest.mark.asyncio
    async def test_find_most_similar(self):
        """Test finding most similar embeddings"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            query_embedding = [1.0, 0.0, 0.0] + [0.0] * 381
            candidate_embeddings = [
                [1.0, 0.0, 0.0] + [0.0] * 381,  # Most similar
                [0.5, 0.5, 0.0] + [0.0] * 381,  # Medium similarity
                [0.0, 1.0, 0.0] + [0.0] * 381,  # Least similar
            ]
            
            result = await generator.find_most_similar(query_embedding, candidate_embeddings, top_k=2)
            
            assert len(result) == 2
            assert result[0][0] == 0  # First candidate should be most similar
            assert result[0][1] > result[1][1]  # First should have higher similarity

    @pytest.mark.asyncio
    async def test_find_most_similar_empty_candidates(self):
        """Test finding most similar with empty candidate list"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            query_embedding = [1.0, 0.0, 0.0] + [0.0] * 381
            result = await generator.find_most_similar(query_embedding, [])
            
            assert result == []

    @pytest.mark.asyncio
    async def test_find_most_similar_with_errors(self):
        """Test finding most similar with some candidates causing errors"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            
            query_embedding = [1.0, 0.0, 0.0] + [0.0] * 381
            candidate_embeddings = [
                [1.0, 0.0, 0.0] + [0.0] * 381,  # Valid
                [0.0, 0.0, 0.0] + [0.0] * 381,  # Valid
                [0.0, 0.0, 0.0] + [0.0] * 381,  # Valid
            ]
            
            # Mock similarity to fail for one candidate
            with patch.object(generator, 'similarity', side_effect=[0.8, Exception("Error"), 0.6]):
                result = await generator.find_most_similar(query_embedding, candidate_embeddings)
                
                # Should handle the error gracefully and return results for valid candidates
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_generate_embedding_with_preprocessing(self):
        """Test embedding generation with text preprocessing"""
        with patch('builtins.__import__') as mock_import:
            mock_sentence_transformers = Mock()
            mock_transformer_class = Mock()
            mock_model = Mock()
            mock_embedding = np.array([0.1, 0.2, 0.3] + [0.0] * 381)
            mock_model.encode.return_value = mock_embedding
            mock_transformer_class.return_value = mock_model
            mock_sentence_transformers.SentenceTransformer = mock_transformer_class
            mock_import.return_value = mock_sentence_transformers
            
            generator = EmbeddingGenerator()
            result = await generator.generate_embedding_with_preprocessing("  TEST TEXT  ")
            
            assert len(result) == 384
            # Verify preprocessing was applied (text should be normalized)
            mock_model.encode.assert_called_once_with("test text")

    def test_model_info_when_not_loaded(self):
        """Test model info when model is not loaded"""
        generator = EmbeddingGenerator.__new__(EmbeddingGenerator)
        generator.model = None
        generator.model_name = "test-model"
        
        info = generator.get_model_info()
        
        assert info["model_name"] == "test-model"
        assert info["is_loaded"] is False
        assert info["type"] == "none"
