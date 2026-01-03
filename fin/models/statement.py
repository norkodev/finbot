"""Statement model for bank statements."""

from sqlalchemy import Column, String, DateTime, Date, Numeric, Text, func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
from datetime import datetime


class Statement(Base):
    """Model for bank statements (estados de cuenta)."""
    
    __tablename__ = 'statements'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Bank information
    bank = Column(String, nullable=False)  # 'bbva', 'hsbc', etc.
    source_type = Column(String, nullable=False)  # 'credit_card', 'debit', etc.
    account_number = Column(String)  # Last 4 digits
    
    # Period information
    period_start = Column(Date)
    period_end = Column(Date)
    statement_date = Column(Date)
    due_date = Column(Date)
    
    # Balance information
    previous_balance = Column(Numeric(12, 2))
    current_balance = Column(Numeric(12, 2))
    minimum_payment = Column(Numeric(12, 2))
    payment_no_interest = Column(Numeric(12, 2))
    credit_limit = Column(Numeric(12, 2))
    available_credit = Column(Numeric(12, 2))
    
    # Summary totals
    total_regular_charges = Column(Numeric(12, 2))
    total_msi_charges = Column(Numeric(12, 2))
    total_interest = Column(Numeric(12, 2))
    total_fees = Column(Numeric(12, 2))
    total_payments = Column(Numeric(12, 2))
    
    # Source file
    source_file = Column(String, nullable=False)
    raw_data = Column(Text)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    
    # Relationships
    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")
    installment_plans = relationship("InstallmentPlan", back_populates="statement", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Statement {self.bank} {self.period_end} - {self.account_number}>"
