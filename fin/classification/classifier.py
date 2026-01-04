"""Main transaction classifier."""

from sqlalchemy.orm import Session
from .rules import RuleEngine
from fin.models import Transaction, Merchant
from typing import Optional

# Try to import LLM classifier (optional dependency)
try:
    from .llm_classifier import LLMClassifier
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class TransactionClassifier:
    """
    Main classifier that orchestrates different classification methods.
    
    Order of precedence:
    1. Merchant History (Learning from corrections)
    2. Rule Engine (Deterministic regex)
    3. LLM Classification (Fallback) - if enabled
    """
    
    def __init__(
        self,
        rule_engine: Optional[RuleEngine] = None,
        use_llm: bool = True,
        llm_model: str = "qwen2.5:7b"
    ):
        """Initialize classifier.
        
        Args:
            rule_engine: Rule engine instance (creates default if None)
            use_llm: Whether to use LLM fallback
            llm_model: LLM model name for Ollama
        """
        self.rule_engine = rule_engine or RuleEngine()
        self.use_llm = use_llm and LLM_AVAILABLE
        
        if self.use_llm:
            try:
                self.llm_classifier = LLMClassifier(model=llm_model)
                # Check if Ollama is available
                if not self.llm_classifier.health_check():
                    print("Warning: Ollama not available, LLM classification disabled")
                    self.use_llm = False
            except Exception as e:
                print(f"Warning: Failed to initialize LLM classifier: {e}")
                self.use_llm = False
        else:
            self.llm_classifier = None
        
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
        
        # 4. Try LLM (if enabled and not classified yet)
        if not classified and self.use_llm:
            # Note: LLM works better in batch mode, but we support single transaction
            try:
                trans_dict = {
                    'id': transaction.id or 0,
                    'description': transaction.description_normalized or transaction.description,
                    'amount': float(transaction.amount) if transaction.amount else 0
                }
                
                results = self.llm_classifier.classify_batch([trans_dict])
                
                if results and len(results) > 0:
                    category, subcategory, confidence = results[0]
                    
                    if category and confidence > 0.5:  # Minimum confidence threshold
                        transaction.category = category
                        transaction.subcategory = subcategory
                        transaction.classification_source = 'llm'
                        transaction.classification_confidence = confidence
                        
                        # Auto-teach merchant from LLM
                        merchant.category = category
                        merchant.subcategory = subcategory
                        
                        classified = True
            
            except Exception as e:
                # LLM errors shouldn't break classification
                print(f"LLM classification error: {e}")
        
        # Update merchant stats (simple counter for now)
        # We don't commit here, caller handles it
        
        return classified
        
    def classify_batch(self, session: Session, transactions: list[Transaction]) -> int:
        """
        Classify a batch of transactions.
        
        Uses optimized batch processing for LLM fallback.
        
        Args:
            session: Database session
            transactions: List of transactions
            
        Returns:
            Number of transactions successfully classified
        """
        # First pass: classify with history and rules
        unclassified = []
        count = 0
        
        for t in transactions:
            # Try merchant history and rules
            if self._classify_with_rules(session, t):
                count += 1
            else:
                unclassified.append(t)
        
        # Second pass: batch LLM classification for unclassified
        if unclassified and self.use_llm:
            try:
                # Prepare batch
                trans_dicts = [
                    {
                        'id': t.id or idx,
                        'description': t.description_normalized or t.description,
                        'amount': float(t.amount) if t.amount else 0
                    }
                    for idx, t in enumerate(unclassified)
                ]
                
                # Classify batch
                results = self.llm_classifier.classify_batch(trans_dicts, max_batch_size=20)
                
                # Apply results
                for t, (category, subcategory, confidence) in zip(unclassified, results):
                    if category and confidence > 0.5:
                        t.category = category
                        t.subcategory = subcategory
                        t.classification_source = 'llm'
                        t.classification_confidence = confidence
                        
                        # Teach merchant
                        if t.merchant_id:
                            merchant = session.query(Merchant).get(t.merchant_id)
                            if merchant:
                                merchant.category = category
                                merchant.subcategory = subcategory
                        
                        count += 1
            
            except Exception as e:
                print(f"Batch LLM classification error: {e}")
        
        return count
    
    def _classify_with_rules(self, session: Session, transaction: Transaction) -> bool:
        """Helper to classify using merchant history and rules only (no LLM)."""
        if not transaction.description:
            return False
            
        from fin.utils import extract_merchant_name, normalize_description
        
        # 1. Identify Merchant
        merchant_name = extract_merchant_name(transaction.description)
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
            session.flush()
            
        # Link transaction to merchant
        transaction.merchant_id = merchant.id
        
        classified = False
        
        # 2. Check Merchant History
        if merchant.category:
            transaction.category = merchant.category
            transaction.subcategory = merchant.subcategory
            transaction.classification_source = 'merchant_history'
            transaction.classification_confidence = 1.0
            classified = True
            
        # 3. Try Rule Engine
        if not classified:
            category, subcategory, confidence = self.rule_engine.classify(transaction.description_normalized)
            
            if category:
                transaction.category = category
                transaction.subcategory = subcategory
                transaction.classification_source = 'rule_engine'
                transaction.classification_confidence = confidence
                
                # Auto-teach merchant
                merchant.category = category
                merchant.subcategory = subcategory
                
                classified = True
        
        return classified
