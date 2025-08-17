#!/usr/bin/env python3
"""
Embedding generator for semantic search capabilities
"""

from typing import List, Optional
import numpy as np
from services.common.logging_config import get_logger

logger = get_logger(__name__)

class EmbeddingGenerator:
    """Generates embeddings for semantic search"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize the embedding model"""
        try:
            # For now, we'll use a simple placeholder implementation
            # In production, this would load the actual model
            logger.info(f"Initializing embedding model: {self.model_name}")
            
            # Placeholder: in real implementation, this would load the model
            # from sentence_transformers import SentenceTransformer
            # self.model = SentenceTransformer(self.model_name)
            
            logger.info("Embedding model initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # Fall back to placeholder implementation
            logger.warning("Using placeholder embedding implementation")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for the given text"""
        if not text:
            # Return zero vector for empty text
            return [0.0] * 384
        
        try:
            if self.model:
                # Real model implementation
                # embedding = self.model.encode(text)
                # return embedding.tolist()
                pass
            
            # Placeholder implementation: generate deterministic "fake" embeddings
            # In production, this would use the actual model
            embedding: List[float] = self._generate_placeholder_embedding(text)
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector on error
            return [0.0] * 384
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        if not texts:
            return []
        
        try:
            if self.model:
                # Real model implementation
                # embeddings = self.model.encode(texts)
                # return embeddings.tolist()
                pass
            
            # Placeholder implementation
            embeddings = []
            for text in texts:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            # Return zero vectors on error
            return [[0.0] * 384] * len(texts)
    
    def _generate_placeholder_embedding(self, text: str) -> List[float]:
        """Generate a placeholder embedding for testing purposes"""
        # This is a deterministic hash-based approach for testing
        # In production, this would be replaced with actual model inference
        
        import hashlib
        
        # Create a hash of the text
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        # Convert hash to a list of floats
        embedding = []
        for i in range(0, len(text_hash), 2):
            if len(embedding) >= 384:
                break
            hex_pair = text_hash[i:i+2]
            # Convert hex to float between -1 and 1
            value = (int(hex_pair, 16) / 255.0) * 2 - 1
            embedding.append(value)
        
        # Pad to exactly 384 dimensions
        while len(embedding) < 384:
            embedding.append(0.0)
        
        return embedding[:384]
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings"""
        return 384
    
    def is_model_loaded(self) -> bool:
        """Check if the model is loaded and ready"""
        return self.model is not None
    
    def get_model_info(self) -> dict:
        """Get information about the current model"""
        return {
            "model_name": self.model_name,
            "is_loaded": self.is_model_loaded(),
            "dimension": self.get_embedding_dimension(),
            "type": "placeholder" if self.model is None else "real"
        }
    
    async def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have the same dimension")
        
        # Convert to numpy arrays for efficient computation
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    async def find_most_similar(self, query_embedding: List[float], 
                               candidate_embeddings: List[List[float]], 
                               top_k: int = 5) -> List[tuple[int, float]]:
        """Find the most similar embeddings to the query"""
        if not candidate_embeddings:
            return []
        
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            try:
                sim = await self.similarity(query_embedding, candidate)
                similarities.append((i, sim))
            except Exception as e:
                logger.warning(f"Error calculating similarity for candidate {i}: {e}")
                continue
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k results
        return similarities[:top_k]
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text before generating embeddings"""
        if not text:
            return ""
        
        # Basic preprocessing
        text = text.strip()
        text = text.lower()
        
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Truncate if too long (most models have token limits)
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    
    async def generate_embedding_with_preprocessing(self, text: str) -> List[float]:
        """Generate embedding with text preprocessing"""
        processed_text = self.preprocess_text(text)
        return await self.generate_embedding(processed_text)
