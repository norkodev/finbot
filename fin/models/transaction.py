"""Transaction model for bank transactions."""

from sqlalchemy import Column, String, DateTime, Date, Numeric, Boolean, Text, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
from datetime import datetime


class Transaction(Base):
    """Model for bank transactions."""
    
    __tablename__ = 'transactions'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to statement
    statement_id = Column(String, ForeignKey('statements.id'))
    
    # Transaction information
    date = Column(Date, nullable=False)
    post_date = Column(Date)
    description = Column(Text, nullable=False)
    description_normalized = Column(Text)
    
    # Amount information
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String, default='MXN')
    
    # Transaction type
    transaction_type = Column(String, nullable=False)  # 'expense', 'income', 'payment', 'interest', 'fee'
    has_interest = Column(Boolean, default=False)
    
    # Classification
    category = Column(String)
    subcategory = Column(String)
    merchant_id = Column(String, ForeignKey('merchants.id'))
    classification_source = Column(String)  # 'rules', 'llm', 'manual'
    classification_confidence = Column(Numeric(3, 2))
    
    # Flags
    is_recurring = Column(Boolean, default=False)
    is_subscription = Column(Boolean, default=False)
    is_reversal = Column(Boolean, default=False)
    is_installment_payment = Column(Boolean, default=False)
    
    # Installment information
    installment_plan_id = Column(String, ForeignKey('installment_plans.id'))
    
    # Metadata
    tags = Column(Text)  # JSON array
    raw_data = Column(Text)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    
    # Relationships
    statement = relationship("Statement", back_populates="transactions")
    merchant = relationship("Merchant", back_populates="transactions")
    installment_plan = relationship("InstallmentPlan", back_populates="payment_transactions")
    
    # Indexes
    __table_args__ = (
        Index('idx_transactions_date', 'date'),
        Index('idx_transactions_category', 'category'),
        Index('idx_transactions_statement', 'statement_id'),
        Index('idx_transactions_merchant', 'merchant_id'),
    )
    
    def __repr__(self):
        return f"<Transaction {self.date} {self.description[:30]} ${self.amount}>"
