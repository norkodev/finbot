"""InstallmentPlan model for MSI (Meses Sin Intereses)."""

from sqlalchemy import Column, String, DateTime, Date, Numeric, Boolean, Integer, Text, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from .database import Base
import uuid
from datetime import datetime
from dateutil.relativedelta import relativedelta


class InstallmentPlan(Base):
    """Model for installment plans (MSI - Meses Sin Intereses)."""
    
    __tablename__ = 'installment_plans'
    
    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to statement
    statement_id = Column(String, ForeignKey('statements.id'))
    
    # Plan information
    description = Column(Text, nullable=False)
    original_amount = Column(Numeric(12, 2), nullable=False)
    pending_balance = Column(Numeric(12, 2))
    monthly_payment = Column(Numeric(12, 2))
    
    # Installment details
    current_installment = Column(Integer)  # e.g., 5 (of 12)
    total_installments = Column(Integer)
    
    # Dates
    start_date = Column(Date)
    end_date_calculated = Column(Date)
    
    # Interest information
    has_interest = Column(Boolean, default=False)
    interest_rate = Column(Numeric(5, 2))  # e.g., 31.00 (%)
    interest_this_period = Column(Numeric(12, 2))
    
    # Source and type
    source_bank = Column(String, nullable=False)
    plan_type = Column(String)  # 'msi', 'efectivo_inmediato', 'balance_transfer'
    status = Column(String, default='active')  # 'active', 'completed', 'cancelled'
    
    # Metadata
    raw_data = Column(Text)  # JSON string
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    
    # Relationships
    statement = relationship("Statement", back_populates="installment_plans")
    payment_transactions = relationship("Transaction", back_populates="installment_plan")
    
    # Indexes
    __table_args__ = (
        Index('idx_installments_end_date', 'end_date_calculated'),
        Index('idx_installments_status', 'status'),
    )
    
    def calculate_end_date(self):
        """Calculate end date based on start date and total installments."""
        if self.start_date and self.total_installments:
            self.end_date_calculated = self.start_date + relativedelta(months=self.total_installments)
    
    def __repr__(self):
        return f"<InstallmentPlan {self.description[:30]} {self.current_installment}/{self.total_installments}>"
