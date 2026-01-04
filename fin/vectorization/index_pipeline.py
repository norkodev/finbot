"""Indexing pipeline for document generation and vectorization."""

from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from typing import List, Dict
from pathlib import Path
import re

from fin.reports import (
    generate_monthly_summary,
    generate_commitments_report,
    generate_merchant_profiles
)
from fin.vectorization import EmbeddingGenerator, FinancialVectorStore


class IndexPipeline:
    """
    Pipeline to generate financial documents and index them in vector store.
    
    Orchestrates:
    1. Document generation (reports)
    2. Markdown chunking
    3. Embedding generation
    4. Storage in ChromaDB
    """
    
    def __init__(self, session: Session):
        """
        Initialize index pipeline.
        
        Args:
            session: Database session
        """
        self.session = session
        self.embedder = EmbeddingGenerator()
        self.vector_store = FinancialVectorStore()
    
    def index_month(self, year: int, month: int, force: bool = False):
        """
        Index all documents for a specific month.
        
        Args:
            year: Year
            month: Month (1-12)
            force: Force reindex even if already exists
        """
        print(f"Indexing {year}-{month:02d}...")
        
        # 1. Generate monthly summary
        summary_md = generate_monthly_summary(self.session, year, month)
        
        # Save to file
        summaries_dir = Path("data/reports/summaries")
        summaries_dir.mkdir(parents=True, exist_ok=True)
        
        summary_file = summaries_dir / f"{year}-{month:02d}.md"
        summary_file.write_text(summary_md, encoding='utf-8')
        
        # 2. Chunk and embed summary
        chunks = self._chunk_markdown(summary_md, max_tokens=800)
        
        if chunks:
            # Delete existing chunks for this month if force
            if force:
                self.vector_store.delete_by_filter({
                    "doc_type": "summary",
                    "month": f"{year}-{month:02d}"
                })
            
            # Generate embeddings (batch)
            embeddings = self.embedder.generate_embeddings_batch(
                chunks,
                show_progress=False
            )
            
            # Store in ChromaDB
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                doc_id = f"summary_{year}_{month:02d}_chunk_{i}"
                self.vector_store.add_document(
                    doc_id=doc_id,
                    text=chunk,
                    embedding=emb,
                    metadata={
                        "doc_type": "summary",
                        "month": f"{year}-{month:02d}",
                        "year": year,
                        "chunk_index": i
                    }
                )
            
            print(f"  ✓ Monthly summary: {len(chunks)} chunks indexed")
        else:
            print(f"  ✓ Monthly summary: empty (no transactions)")
    
    def index_commitments(self, force: bool = False):
        """Index commitments report (single document, updated regularly)."""
        print("Indexing commitments...")
        
        # Generate commitments report
        commitments_md = generate_commitments_report(self.session)
        
        # Save to file
        reports_dir = Path("data/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        commitments_file = reports_dir / "commitments.md"
        commitments_file.write_text(commitments_md, encoding='utf-8')
        
        # Delete existing if force
        if force:
            self.vector_store.delete_by_filter({"doc_type": "commitment"})
        
        # Chunk (usually small, might be single chunk)
        chunks = self._chunk_markdown(commitments_md, max_tokens=800)
        
        if chunks:
            embeddings = self.embedder.generate_embeddings_batch(
                chunks,
                show_progress=False
            )
            
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                doc_id = f"commitment_chunk_{i}"
                self.vector_store.add_document(
                    doc_id=doc_id,
                    text=chunk,
                    embedding=emb,
                    metadata={
                        "doc_type": "commitment",
                        "year": 0,  # Not month-specific
                        "chunk_index": i
                    }
                )
            
            print(f"  ✓ Commitments: {len(chunks)} chunks indexed")
    
    def index_merchants(self, min_transactions: int = 3, force: bool = False):
        """Index merchant profiles."""
        print(f"Indexing merchant profiles (min {min_transactions} trans)...")
        
        # Generate profiles
        profiles = generate_merchant_profiles(
            self.session,
            min_transactions=min_transactions
        )
        
        if not profiles:
            print("  ✓ No merchants to index")
            return
        
        # Save to files
        merchants_dir = Path("data/reports/merchants")
        merchants_dir.mkdir(parents=True, exist_ok=True)
        
        # Delete existing if force
        if force:
            self.vector_store.delete_by_filter({"doc_type": "merchant_profile"})
        
        indexed_count = 0
        
        for merchant_name, profile_md in profiles:
            # Save file
            # Sanitize filename
            safe_name = re.sub(r'[^\w\s-]', '', merchant_name).strip().replace(' ', '_')
            profile_file = merchants_dir / f"{safe_name}.md"
            profile_file.write_text(profile_md, encoding='utf-8')
            
            # Usually merchant profiles are short, single chunk
            embedding = self.embedder.generate_embedding(profile_md)
            
            doc_id = f"merchant_{safe_name}"
            self.vector_store.add_document(
                doc_id=doc_id,
                text=profile_md,
                embedding=embedding,
                metadata={
                    "doc_type": "merchant_profile",
                    "merchant_name": merchant_name,
                    "year": 0,
                    "chunk_index": 0
                }
            )
            
            indexed_count += 1
        
        print(f"  ✓ Merchant profiles: {indexed_count} indexed")
    
    def rebuild_index(self):
        """Rebuild entire index from scratch."""
        print("=" * 60)
        print("Rebuilding entire index...")
        print("=" * 60)
        
        # Get all months with data
        months_with_data = self._get_months_with_data()
        
        print(f"\nFound {len(months_with_data)} months with data")
        print()
        
        # Index each month
        for year, month in months_with_data:
            self.index_month(year, month, force=True)
        
        print()
        
        # Index commitments
        self.index_commitments(force=True)
        
        print()
        
        # Index merchants
        self.index_merchants(force=True)
        
        # Persist changes
        self.vector_store.persist()
        
        print()
        print("=" * 60)
        print("Index rebuild complete!")
        
        # Show stats
        stats = self.vector_store.get_stats()
        print(f"Total documents: {stats['total_documents']}")
        print("=" * 60)
    
    def _get_months_with_data(self) -> List[tuple]:
        """Get all (year, month) tuples that have transactions."""
        from fin.models import Transaction
        
        results = self.session.query(
            extract('year', Transaction.date).label('year'),
            extract('month', Transaction.date).label('month')
        ).distinct().order_by('year', 'month').all()
        
        return [(int(year), int(month)) for year, month in results]
    
    def _chunk_markdown(
        self,
        text: str,
        max_tokens: int = 800
    ) -> List[str]:
        """
        Intelligent markdown chunking.
        
        Strategy:
        - Split on ## headers (keep ### with parent)
        - Target 300-800 tokens per chunk
        - Don't split lists/tables
        
        For now, simple implementation: split on ## headers.
        """
        if not text.strip():
            return []
        
        # Simple chunking: split on ## headers
        chunks = []
        current_chunk = []
        
        lines = text.split('\n')
        
        for line in lines:
            # Check if it's a ## header (but not #)
            if line.startswith('## ') and not line.startswith('### '):
                # Save previous chunk if exists
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if chunk_text:
                        chunks.append(chunk_text)
                
                # Start new chunk with this header
                current_chunk = [line]
            else:
                current_chunk.append(line)
        
        # Don't forget last chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)
        
        # If no ## headers, treat whole document as one chunk
        if not chunks:
            chunks = [text.strip()]
        
        return chunks
