"""Vector store using ChromaDB for semantic search."""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from pathlib import Path


class FinancialVectorStore:
    """Vector store for financial documents using ChromaDB."""
    
    def __init__(self, persist_directory: str = "data/chromadb"):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory for persistent storage
        """
        self.persist_directory = persist_directory
        Path(persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with persistence
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=persist_directory
        ))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="financial_docs",
            metadata={"description": "Financial documents and reports"}
        )
    
    def add_document(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: dict
    ):
        """
        Add document to vector store.
        
        Args:
            doc_id: Unique document ID
            text: Document text content
            embedding: Embedding vector
            metadata: Document metadata
        
        Metadata schema:
            doc_type: str (summary|commitment|merchant_profile)
            month: str (YYYY-MM, optional)
            year: int
            merchant_id: str (optional)
            chunk_index: int (if chunked, default 0)
        """
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
    
    def add_documents_batch(
        self,
        doc_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict]
    ):
        """Add multiple documents in batch (more efficient)."""
        self.collection.add(
            ids=doc_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
    
    def search(
        self,
        query_embedding: List[float],
        filters: Optional[dict] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            filters: Metadata filters (e.g., {"doc_type": "summary"})
            top_k: Number of results to return
        
        Returns:
            List of results with text, metadata, distance
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )
        
        return self._format_results(results)
    
    def search_by_text(
        self,
        query_text: str,
        filters: Optional[dict] = None,
        top_k: int = 5
    ) -> List[dict]:
        """
        Search using text query (ChromaDB will embed it).
        
        Note: Requires embedding function to be set in collection.
        For now, use search() with pre-generated embedding.
        """
        # This would require embedding function in ChromaDB
        # For now, users should call EmbeddingGenerator first
        raise NotImplementedError(
            "Use EmbeddingGenerator.generate_embedding() then search()"
        )
    
    def get_by_id(self, doc_id: str) -> Optional[dict]:
        """Get document by ID."""
        results = self.collection.get(ids=[doc_id])
        
        if results and results['ids']:
            return {
                'id': results['ids'][0],
                'text': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        return None
    
    def delete_by_filter(self, filters: dict) -> int:
        """
        Delete documents matching filters.
        
        Returns number of documents deleted.
        """
        # Query matching documents
        all_results = self.collection.get(where=filters)
        
        if all_results and all_results['ids']:
            ids_to_delete = all_results['ids']
            self.collection.delete(ids=ids_to_delete)
            return len(ids_to_delete)
        
        return 0
    
    def delete_by_id(self, doc_id: str):
        """Delete single document by ID."""
        self.collection.delete(ids=[doc_id])
    
    def get_stats(self) -> dict:
        """Get collection statistics."""
        count = self.collection.count()
        
        return {
            "total_documents": count,
            "collection_name": self.collection.name,
            "persist_directory": self.persist_directory
        }
    
    def _format_results(self, raw_results: dict) -> List[dict]:
        """Format ChromaDB results to consistent structure."""
        formatted = []
        
        if not raw_results or not raw_results.get('ids'):
            return formatted
        
        for i in range(len(raw_results['ids'][0])):
            formatted.append({
                'id': raw_results['ids'][0][i],
                'text': raw_results['documents'][0][i],
                'metadata': raw_results['metadatas'][0][i],
                'distance': raw_results['distances'][0][i] if 'distances' in raw_results else None
            })
        
        return formatted
    
    def persist(self):
        """Explicitly persist changes to disk."""
        self.client.persist()
