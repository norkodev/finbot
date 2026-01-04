"""Retrieval engine for RAG with semantic search and metadata filtering."""

from typing import List, Dict, Optional
from datetime import datetime
import re

from fin.vectorization import EmbeddingGenerator, FinancialVectorStore


class RetrievalEngine:
    """Hybrid retrieval engine for financial documents."""
    
    def __init__(self):
        """Initialize retrieval engine with embeddings and vector store."""
        self.embedder = EmbeddingGenerator()
        self.vector_store = FinancialVectorStore()
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: User question in natural language
            top_k: Number of results to return
            filters: Optional metadata filters to apply
        
        Returns:
            List of documents with text, metadata, and relevance score
        """
        # 1. Extract filters from natural language query
        extracted_filters = self._extract_filters(query)
        
        # 2. Merge with provided filters (provided filters take precedence)
        final_filters = {**extracted_filters, **(filters or {})}
        
        # 3. Generate embedding for query
        query_embedding = self.embedder.generate_embedding(query)
        
        # 4. Search in vector store
        results = self.vector_store.search(
            query_embedding,
            filters=final_filters if final_filters else None,
            top_k=top_k
        )
        
        return results
    
    def _extract_filters(self, query: str) -> Dict:
        """
        Extract metadata filters from natural language query.
        
        Detects:
        - Months (in Spanish)
        - Document types (summary, commitment, merchant_profile)
        - Categories
        
        Returns:
            Dictionary of metadata filters
        """
        filters = {}
        query_lower = query.lower()
        
        # Month extraction (Spanish months)
        month_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
            'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
            'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        
        for month_name, month_num in month_map.items():
            if month_name in query_lower:
                # Get current year (or could extract from query)
                current_year = datetime.now().year
                filters['month'] = f"{current_year}-{month_num:02d}"
                filters['year'] = current_year
                break
        
        # Detect "mes pasado" (last month)
        if 'mes pasado' in query_lower or 'último mes' in query_lower:
            now = datetime.now()
            last_month = now.month - 1 if now.month > 1 else 12
            year = now.year if now.month > 1 else now.year - 1
            filters['month'] = f"{year}-{last_month:02d}"
            filters['year'] = year
        
        # Detect "este mes" (this month)
        if 'este mes' in query_lower:
            now = datetime.now()
            filters['month'] = f"{now.year}-{now.month:02d}"
            filters['year'] = now.year
        
        # Document type detection
        commitment_keywords = ['compromiso', 'msi', 'pago', 'termina', 'mensualidad', 'suscripcion']
        merchant_keywords = ['comercio', 'tienda', 'oxxo', 'uber', 'amazon', 'dónde', 'donde']
        summary_keywords = ['resumen', 'total', 'gast', 'categor', 'cuánto', 'cuanto']
        
        if any(word in query_lower for word in commitment_keywords):
            filters['doc_type'] = 'commitment'
        elif any(word in query_lower for word in merchant_keywords):
            filters['doc_type'] = 'merchant_profile'
        elif any(word in query_lower for word in summary_keywords):
            filters['doc_type'] = 'summary'
        
        return filters
    
    def extract_intent(self, query: str) -> str:
        """
        Extract user intent from query.
        
        Returns:
            Intent type: 'spending', 'commitment', 'merchant', 'comparison', 'unknown'
        """
        query_lower = query.lower()
        
        # Spending query
        if any(word in query_lower for word in ['gasté', 'gasto', 'cuánto', 'total']):
            return 'spending'
        
        # Commitment query
        if any(word in query_lower for word in ['termina', 'mensualidad', 'msi', 'compromiso']):
            return 'commitment'
        
        # Merchant query
        if any(word in query_lower for word in ['oxxo', 'uber', 'amazon', 'comercio', 'tienda']):
            return 'merchant'
        
        # Comparison query
        if any(word in query_lower for word in ['comparar', 'diferencia', 'más', 'menos']):
            return 'comparison'
        
        return 'unknown'
