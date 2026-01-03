"""Utility functions for money/currency parsing."""

from decimal import Decimal, InvalidOperation
from typing import Optional
import re


def parse_amount(text: str) -> Optional[Decimal]:
    """
    Parse a money amount in Mexican format (e.g., '$1,234.56' or '($100.00)').
    
    Args:
        text: Money amount as string
        
    Returns:
        Decimal value or None if parsing fails
    """
    if not text or not isinstance(text, str):
        return None
    
    # Remove whitespace
    text = text.strip()
    
    # Check for negative amount in parentheses
    is_negative = False
    if text.startswith('(') and text.endswith(')'):
        is_negative = True
        text = text[1:-1]
    
    # Remove currency symbols and whitespace
    text = re.sub(r'[\$\s]', '', text)
    
    # Remove thousands separators (commas)
    text = text.replace(',', '')
    
    # Handle dash or empty as zero
    if text == '-' or text == '':
        return Decimal('0')
    
    try:
        amount = Decimal(text)
        return -amount if is_negative else amount
    except (InvalidOperation, ValueError):
        return None


def format_amount_mexican(amount: Decimal) -> str:
    """
    Format amount in Mexican currency format.
    
    Args:
        amount: Decimal amount
        
    Returns:
        Formatted string (e.g., '$1,234.56')
    """
    if amount is None:
        return "$0.00"
    
    # Format with thousands separator
    formatted = f"${amount:,.2f}"
    
    return formatted
