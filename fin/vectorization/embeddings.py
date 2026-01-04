"""Embedding generation using sentence-transformers."""

from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np


class EmbeddingGenerator:
    """Generate embeddings using local sentence-transformers model."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Name of sentence-transformers model
                       Default: all-MiniLM-L6-v2 (384 dimensions, 90MB)
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for single text.
        
        Args:
            text: Input text
        
        Returns:
            List of floats (embedding vector)
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> List[List[float]]:
        """
        Generate embeddings for batch of texts (more efficient).
        
        Args:
            texts: List of input texts
            batch_size: Batch size for encoding
            show_progress: Show progress bar
        
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def cosine_similarity(
        self,
        embedding1: Union[List[float], np.ndarray],
        embedding2: Union[List[float], np.ndarray]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
        
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)
        
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
    
    def find_most_similar(
        self,
        query_text: str,
        candidate_texts: List[str],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar texts to query.
        
        Args:
            query_text: Query text
            candidate_texts: List of candidate texts
            top_k: Number of top results to return
        
        Returns:
            List of (index, text, similarity_score) tuples
        """
        query_emb = self.generate_embedding(query_text)
        candidate_embs = self.generate_embeddings_batch(candidate_texts, show_progress=False)
        
        similarities = [
            (i, text, self.cosine_similarity(query_emb, emb))
            for i, (text, emb) in enumerate(zip(candidate_texts, candidate_embs))
        ]
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[2], reverse=True)
        
        return similarities[:top_k]
