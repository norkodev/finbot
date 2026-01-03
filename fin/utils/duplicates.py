"""Utilities for detecting duplicate and reversed transactions."""

from sqlalchemy.orm import Session
from fin.models import Transaction
from collections import defaultdict
from datetime import timedelta


def detect_duplicates(session: Session, statement_id: int) -> int:
    """
    Detect duplicate transactions within a statement.
    
    Args:
        session: Database session
        statement_id: ID of the statement to check
        
    Returns:
        Number of duplicates found
    """
    # Get all transactions for this statement
    transactions = session.query(Transaction).filter_by(
        statement_id=statement_id
    ).all()
    
    # Group by (date, amount, normalized_description)
    groups = defaultdict(list)
    for t in transactions:
        key = (t.date, t.amount, t.description_normalized)
        groups[key].append(t)
    
    # Mark duplicates (keep first, flag others)
    duplicates_count = 0
    for group in groups.values():
        if len(group) > 1:
            # Keep the first one, mark others as duplicates
            for t in group[1:]:
                if not t.is_duplicate:
                    t.is_duplicate = True
                    duplicates_count += 1
    
    return duplicates_count


def detect_reversals(session: Session, statement_id: int) -> int:
    """
    Detect reversal pairs (charge + refund that cancel each other).
    
    Args:
        session: Database session
        statement_id: ID of the statement to check
        
    Returns:
        Number of reversals found
    """
    # Get all transactions ordered by date
    transactions = session.query(Transaction).filter_by(
        statement_id=statement_id
    ).order_by(Transaction.date).all()
    
    reversals_count = 0
    
    # Look for same amount opposite sign within 3 days
    for i, t1 in enumerate(transactions):
        # Skip if already marked as reversal
        if t1.is_reversal:
            continue
            
        for t2 in transactions[i+1:]:
            # Only check within 3 days
            if (t2.date - t1.date).days > 3:
                break
            
            # Skip if already marked
            if t2.is_reversal:
                continue
            
            # Check if they cancel each other
            if (abs(float(t1.amount) + float(t2.amount)) < 0.01 and  # Opposite amounts
                t1.description_normalized == t2.description_normalized):  # Same description
                # Mark both as reversals
                t1.is_reversal = True
                t2.is_reversal = True
                t2.related_transaction_id = t1.id
                reversals_count += 2
                break  # Don't check more for t1
    
    return reversals_count


def detect_all(session: Session, statement_id: int) -> dict:
    """
    Run all detection algorithms on a statement.
    
    Args:
        session: Database session
        statement_id: ID of the statement to check
        
    Returns:
        Dictionary with detection results
    """
    duplicates = detect_duplicates(session, statement_id)
    reversals = detect_reversals(session, statement_id)
    
    return {
        'duplicates': duplicates,
        'reversals': reversals,
        'total_flagged': duplicates + reversals
    }
