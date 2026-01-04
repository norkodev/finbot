"""Financial calculations for projections and analysis."""

from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from decimal import Decimal

from fin.models import Transaction, InstallmentPlan, Merchant


class FinancialCalculator:
    """Calculate financial metrics, averages, and projections."""
    
    def __init__(self, session: Session):
        """
        Initialize calculator with database session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
    
    def calculate_category_total(
        self,
        category: str,
        start_date: datetime,
        end_date: datetime
    ) -> Decimal:
        """
        Calculate total spending in a category for a period.
        
        Args:
            category: Category name
            start_date: Start date
            end_date: End date
        
        Returns:
            Total amount spent
        """
        transactions = self.session.query(Transaction).filter(
            Transaction.category == category,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.transaction_type == 'expense'
        ).all()
        
        total = sum(abs(Decimal(str(t.amount))) for t in transactions)
        return total
    
    def calculate_average_monthly(
        self,
        category: str = None,
        merchant_name: str = None,
        months_back: int = 6
    ) -> Decimal:
        """
        Calculate average monthly spending.
        
        Args:
            category: Optional category filter
            merchant_name: Optional merchant filter
            months_back: Number of months to analyze
        
        Returns:
            Average monthly amount
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=months_back * 30)
        
        query = self.session.query(Transaction).filter(
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.transaction_type == 'expense'
        )
        
        if category:
            query = query.filter(Transaction.category == category)
        
        if merchant_name:
            # Find merchant
            merchant = self.session.query(Merchant).filter(
                func.lower(Merchant.name).like(f"%{merchant_name.lower()}%")
            ).first()
            
            if merchant:
                query = query.filter(Transaction.merchant_id == merchant.id)
        
        transactions = query.all()
        
        if not transactions:
            return Decimal('0')
        
        total = sum(abs(Decimal(str(t.amount))) for t in transactions)
        return total / months_back if months_back > 0 else Decimal('0')
    
    def project_savings(
        self,
        current_monthly: float,
        target_monthly: float,
        months: int
    ) -> Dict:
        """
        Project savings from reducing spending.
        
        Args:
            current_monthly: Current monthly spending
            target_monthly: Target monthly spending
            months: Number of months
        
        Returns:
            Dictionary with projection details
        """
        monthly_reduction = current_monthly - target_monthly
        total_savings = monthly_reduction * months
        percentage_reduction = (monthly_reduction / current_monthly * 100) if current_monthly > 0 else 0
        
        return {
            'current_monthly': current_monthly,
            'target_monthly': target_monthly,
            'monthly_reduction': monthly_reduction,
            'percentage_reduction': percentage_reduction,
            'months': months,
            'total_savings': total_savings
        }
    
    def calculate_debt_cost(
        self,
        plan_id: str = None
    ) -> Dict:
        """
        Calculate total interest cost for installment plans.
        
        Args:
            plan_id: Optional specific plan ID, otherwise all active
        
        Returns:
            Dictionary with debt cost breakdown
        """
        query = self.session.query(InstallmentPlan)
        
        if plan_id:
            query = query.filter(InstallmentPlan.id == plan_id)
        else:
            query = query.filter(InstallmentPlan.status == 'active')
        
        plans = query.all()
        
        total_debt = Decimal('0')
        total_paid = Decimal('0')
        total_interests = Decimal('0')
        
        for plan in plans:
            if plan.original_amount:
                total_debt += Decimal(str(plan.original_amount))
            
            if plan.original_amount and plan.pending_balance:
                paid = Decimal(str(plan.original_amount)) - Decimal(str(plan.pending_balance))
                total_paid += paid
                
                # Estimate interests (simplified)
                if plan.total_installments and plan.monthly_payment:
                    total_payments = Decimal(str(plan.monthly_payment)) * plan.total_installments
                    interests = total_payments - Decimal(str(plan.original_amount))
                    total_interests += max(Decimal('0'), interests)
        
        return {
            'total_original_debt': float(total_debt),
            'total_paid_so_far': float(total_paid),
            'total_interests_paid': float(total_interests),
            'total_pending': float(total_debt - total_paid),
            'active_plans': len(plans)
        }
    
    def get_ending_soon_commitments(
        self,
        months_ahead: int = 3
    ) -> List[Dict]:
        """
        Get MSI plans that end in the next N months.
        
        Args:
            months_ahead: Number of months to look ahead
        
        Returns:
            List of commitments ending soon
        """
        plans = self.session.query(InstallmentPlan).filter(
            InstallmentPlan.status == 'active',
            InstallmentPlan.pending_balance > 0
        ).all()
        
        ending_soon = []
        cutoff_date = datetime.now().date() + timedelta(days=months_ahead * 30)
        
        for plan in plans:
            if plan.end_date_calculated and plan.end_date_calculated <= cutoff_date:
                ending_soon.append({
                    'description': plan.description,
                    'monthly_payment': float(plan.monthly_payment) if plan.monthly_payment else 0,
                    'end_date': plan.end_date_calculated,
                    'months_remaining': (plan.end_date_calculated.year - datetime.now().year) * 12 +
                                       (plan.end_date_calculated.month - datetime.now().month)
                })
        
        return ending_soon
