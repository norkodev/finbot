"""Subscription and recurring payment detection."""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from fin.models import Transaction, Merchant
from typing import List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal


class SubscriptionDetector:
    """Detect recurring payments and subscriptions."""
    
    # Known subscription services
    KNOWN_SUBSCRIPTIONS = {
        'netflix', 'spotify', 'amazon prime', 'disney', 'hbo', 'apple music',
        'youtube premium', 'google one', 'icloud', 'dropbox', 'office 365',
        'microsoft 365', 'github', 'linkedin premium', 'zoom', 'adobe',
        'smartfit', 'sportcity', 'gold gym', 'anytime fitness'
    }
    
    def __init__(
        self,
        min_occurrences: int = 2,
        amount_tolerance: float = 0.1,  # 10% tolerance
        period_tolerance_days: int = 7   # ±7 days for monthly
    ):
        """
        Initialize subscription detector.
        
        Args:
            min_occurrences: Minimum transactions to consider subscription
            amount_tolerance: Maximum % difference in amount (0.1 = 10%)
            period_tolerance_days: Tolerance for monthly periodicity (days)
        """
        self.min_occurrences = min_occurrences
        self.amount_tolerance = amount_tolerance
        self.period_tolerance_days = period_tolerance_days
    
    def detect_subscriptions(self, session: Session) -> List[dict]:
        """
        Detect all subscriptions in database.
        
        Returns:
            List of subscription dicts with merchant, amount, frequency, etc.
        """
        subscriptions = []
        
        # Group transactions by merchant
        merchants = session.query(Merchant).all()
        
        for merchant in merchants:
            # Get all transactions for this merchant
            transactions = session.query(Transaction).filter(
                and_(
                    Transaction.merchant_id == merchant.id,
                    Transaction.transaction_type == 'expense'  # Only charges, not payments
                )
            ).order_by(Transaction.date).all()
            
            if len(transactions) < self.min_occurrences:
                continue
            
            # Check if it's a subscription
            subscription_info = self._analyze_merchant_transactions(
                merchant, transactions
            )
            
            if subscription_info:
                subscriptions.append(subscription_info)
        
        return subscriptions
    
    def _analyze_merchant_transactions(
        self,
        merchant: Merchant,
        transactions: List[Transaction]
    ) -> dict | None:
        """
        Analyze if merchant transactions form a subscription pattern.
        
        Returns:
            Subscription info dict or None if not a subscription
        """
        if len(transactions) < self.min_occurrences:
            return None
        
        # Check if it's a known subscription
        is_known = any(
            sub in merchant.normalized_name.lower()
            for sub in self.KNOWN_SUBSCRIPTIONS
        )
        
        # Get amounts
        amounts = [abs(float(t.amount)) for t in transactions]
        avg_amount = sum(amounts) / len(amounts)
        
        # Check amount consistency
        amount_stdev = (sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)) ** 0.5
        amount_variation = amount_stdev / avg_amount if avg_amount > 0 else 1.0
        
        # If too much variation, not a subscription (unless known)
        if amount_variation > self.amount_tolerance and not is_known:
            return None
        
        # Check periodicity (monthly pattern)
        dates = [t.date for t in transactions]
        
        if len(dates) < 2:
            return None
        
        # Calculate intervals between transactions
        intervals = []
        for i in range(1, len(dates)):
            delta = (dates[i] - dates[i-1]).days
            intervals.append(delta)
        
        if not intervals:
            return None
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Check if approximately monthly (28-32 days)
        is_monthly = 20 <= avg_interval <= 40
        
        # Determine frequency
        if is_monthly:
            frequency = 'monthly'
        elif avg_interval < 20:
            frequency = 'frequent'  # Could be weekly, biweekly
        else:
            frequency = 'irregular'
        
        # Only report if monthly pattern or known subscription
        if not (is_monthly or is_known):
            return None
        
        # Build subscription info
        return {
            'merchant_id': merchant.id,
            'merchant_name': merchant.name,
            'average_amount': Decimal(str(avg_amount)).quantize(Decimal('0.01')),
            'frequency': frequency,
            'count': len(transactions),
            'first_payment': dates[0],
            'last_payment': dates[-1],
            'is_known_subscription': is_known,
            'category': merchant.category,
            'subcategory': merchant.subcategory,
            'amount_variation': amount_variation
        }
    
    def mark_subscription_transactions(self, session: Session):
        """Mark transactions that are part of subscriptions."""
        subscriptions = self.detect_subscriptions(session)
        
        marked_count = 0
        
        for sub in subscriptions:
            # Update all transactions for this merchant as subscription
            transactions = session.query(Transaction).filter(
                Transaction.merchant_id == sub['merchant_id']
            ).all()
            
            for trans in transactions:
                if not trans.is_subscription:
                    trans.is_subscription = True
                    marked_count += 1
        
        session.commit()
        
        return marked_count, len(subscriptions)


def get_active_subscriptions(session: Session, months_back: int = 3) -> List[dict]:
    """
    Get currently active subscriptions (detected in last N months).
    
    Args:
        session: Database session
        months_back: How many months back to check for activity
    
    Returns:
        List of active subscription dicts
    """
    detector = SubscriptionDetector()
    all_subs = detector.detect_subscriptions(session)
    
    # Filter to only recent ones
    cutoff_date = datetime.now().date() - timedelta(days=months_back * 30)
    
    active = [
        sub for sub in all_subs
        if sub['last_payment'] >= cutoff_date
    ]
    
    # Sort by amount (descending)
    active.sort(key=lambda x: x['average_amount'], reverse=True)
    
    return active
