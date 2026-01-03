"""Main transaction classifier."""

from sqlalchemy.orm import Session
from .rules import RuleEngine
from fin.models import Transaction, Merchant
from typing import Optional


class TransactionClassifier:
    """
    Main classifier that orchestrates different classification methods.
    
    Order of precedence:
    1. Rule Engine (Deterministic regex)
    2. Merchant History (Learning from corrections) - To be implemented
    3. LLM Classification (Fallback) - To be implemented
    """
    
    def __init__(self, rule_engine: Optional[RuleEngine] = None):
        """Initialize classifier."""
        self.rule_engine = rule_engine or RuleEngine()
        
    def classify_transaction(self, session: Session, transaction: Transaction) -> bool:
        """
        Classify a single transaction.
        
        Args:
            session: Database session
            transaction: Transaction object to classify
            
        Returns:
            True if classified, False otherwise
        """
        if not transaction.description:
            return False
            
        from fin.utils import extract_merchant_name, normalize_description
        
        # 1. Identify Merchant
        # Extract clean name
        merchant_name = extract_merchant_name(transaction.description)
        # Normalize for deduplication (UPPERCASE, NO ACCENTS)
        norm_name = normalize_description(merchant_name)
        
        if not norm_name:
            return False
            
        # Find or create merchant
        merchant = session.query(Merchant).filter_by(normalized_name=norm_name).first()
        
        if not merchant:
            merchant = Merchant(
                name=merchant_name,
                normalized_name=norm_name
            )
            session.add(merchant)
            # Flush to get ID if needed, though we assign object directly usually
            session.flush()
            
        # Link transaction to merchant (store ID, not object to avoid SA warning)
        transaction.merchant_id = merchant.id
        
        classified = False
        
        # 2. Check Merchant History (Prioritized)
        if merchant.category:
            transaction.category = merchant.category
            transaction.subcategory = merchant.subcategory
            transaction.classification_source = 'merchant_history'
            transaction.classification_confidence = 1.0
            classified = True
            
        # 3. Try Rule Engine (if not classified by history)
        if not classified:
            category, subcategory, confidence = self.rule_engine.classify(transaction.description_normalized)
            
            if category:
                transaction.category = category
                transaction.subcategory = subcategory
                transaction.classification_source = 'rule_engine'
                transaction.classification_confidence = confidence
                
                # Auto-teach merchant (Bootstrap)
                merchant.category = category
                merchant.subcategory = subcategory
                
                classified = True
        
        # Update merchant stats (simple counter for now)
        # We don't commit here, caller handles it
        
        return classified
        
    def classify_batch(self, session: Session, transactions: list[Transaction]) -> int:
        """
        Classify a batch of transactions.
        
        Args:
            session: Database session
            transactions: List of transactions
            
        Returns:
            Number of transactions successfully classified
        """
        count = 0
        for t in transactions:
            if self.classify_transaction(session, t):
                count += 1
        return count
