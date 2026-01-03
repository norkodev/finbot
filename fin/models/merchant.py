"""Merchant model for commercial establishments catalog."""

from sqlalchemy import Column, String, DateTime, Date, Numeric, Boolean, Integer, Text, Index, func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
from datetime import datetime


class Merchant(Base):
    """Model for merchant catalog."""
    
    __tablename__ = 'merchants'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Merchant information
    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False, unique=True)
    aliases = Column(Text)  # JSON array of name variations
    
    # Classification
    category = Column(String)
    subcategory = Column(String)
    
    # Subscription information
    is_subscription = Column(Boolean, default=False)
    subscription_amount = Column(Numeric(12, 2))
    subscription_frequency = Column(String)  # 'monthly', 'yearly', etc.
    
    # Statistics
    total_transactions = Column(Integer, default=0)
    total_amount = Column(Numeric(12, 2), default=0)
    average_amount = Column(Numeric(12, 2))
    last_transaction_date = Column(Date)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="merchant")
    
    # Indexes
    __table_args__ = (
        Index('idx_merchants_normalized', 'normalized_name'),
    )
    
    def update_statistics(self, session):
        """Update merchant statistics based on transactions."""
        from sqlalchemy import func as sqlfunc
        from .transaction import Transaction
        
        # Get count and sum
        stats = session.query(
            sqlfunc.count(Transaction.id).label('count'),
            sqlfunc.sum(Transaction.amount).label('total'),
            sqlfunc.avg(Transaction.amount).label('average'),
            sqlfunc.max(Transaction.date).label('last_date')
        ).filter(
            Transaction.merchant_id == self.id
        ).first()
        
        if stats:
            self.total_transactions = stats.count or 0
            self.total_amount = stats.total or 0
            self.average_amount = stats.average or 0
            self.last_transaction_date = stats.last_date
    
    def __repr__(self):
        return f"<Merchant {self.name} ({self.category})>"
