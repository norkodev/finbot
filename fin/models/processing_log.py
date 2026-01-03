"""ProcessingLog model for tracking PDF processing."""

from sqlalchemy import Column, String, DateTime, Integer, Text, Index, func
from .database import Base
import uuid
from datetime import datetime


class ProcessingLog(Base):
    """Model for tracking processed files."""
    
    __tablename__ = 'processing_log'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File information
    file_path = Column(String, nullable=False)
    file_hash = Column(String, nullable=False)  # SHA256
    file_size = Column(Integer)
    
    # Processing information
    bank_detected = Column(String)
    processing_status = Column(String)  # 'success', 'error', 'partial'
    error_message = Column(Text)
    
    # Counts
    statements_created = Column(Integer, default=0)
    transactions_created = Column(Integer, default=0)
    installments_created = Column(Integer, default=0)
    
    # Timestamp
    processed_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_processing_file_hash', 'file_hash'),
    )
    
    def __repr__(self):
        return f"<ProcessingLog {self.file_path} - {self.processing_status}>"
