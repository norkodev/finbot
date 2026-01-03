"""Utility functions for text normalization and extraction."""

from unidecode import unidecode
import re
from typing import Optional, Tuple


def normalize_description(text: str) -> str:
    """
    Normalize transaction description for matching and classification.
    
    - Converts to uppercase
    - Removes accents
    - Collapses multiple spaces
    - Removes special characters
    
    Args:
        text: Original description
        
    Returns:
        Normalized description
    """
    if not text:
        return ""
    
    # Convert to uppercase
    text = text.upper()
    
    # Remove accents
    text = unidecode(text)
    
    # Remove special characters except spaces and alphanumeric
    text = re.sub(r'[^A-Z0-9\s]', ' ', text)
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_card_digits(text: str) -> Optional[str]:
    """
    Extract card digits from description (e.g., '***1234').
    
    Args:
        text: Description text
        
    Returns:
        Card digits or None
    """
    if not text:
        return None
    
    match = re.search(r'\*+(\d{4})', text)
    if match:
        return match.group(1)
    
    return None


def extract_installment_info(text: str) -> Optional[Tuple[int, int]]:
    """
    Extract installment information from description (e.g., '5 DE 12').
    
    Args:
        text: Description text
        
    Returns:
        Tuple of (current, total) or None
    """
    if not text:
        return None
    
    # Match patterns like "5 DE 12" or "05 DE 12"
    match = re.search(r'(\d+)\s+DE\s+(\d+)', text.upper())
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        return (current, total)
    
    return None


def clean_merchant_name(text: str) -> str:
    """
    Clean merchant name by removing common noise.
    
    Args:
        text: Raw merchant name
        
    Returns:
        Cleaned merchant name
    """
    if not text:
        return ""
    
    # Normalize first
    text = normalize_description(text)
    
    # Remove card digit references
    text = re.sub(r'TARJETA\s+DIGITAL\s+\*+\d+', '', text)
    text = re.sub(r'\*+\d{4}', '', text)
    
    # Remove installment info
    text = re.sub(r'\d+\s+DE\s+\d+', '', text)
    
    # Remove common separators at the end
    text = re.sub(r'\s*[;,]\s*$', '', text)
    
    # Remove location codes at the end (3-4 uppercase letters)
    text = re.sub(r'\s+[A-Z]{3,4}$', '', text)
    
    # Collapse spaces again
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_merchant_name(description: str) -> str:
    """
    Extract clean merchant name from transaction description.
    
    This is the main function to use for getting merchant names.
    It applies all cleaning rules in the correct order.
    
    Args:
        description: Raw transaction description
        
    Returns:
        Clean merchant name
    """
    if not description:
        return ""
    
    # Start with raw text
    text = description
    
    # Remove card references first
    text = re.sub(r'Tarjeta Digital \*+\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\*+\d{4}', '', text)
    
    # Remove installment references
    text = re.sub(r'\d+\s+[Dd][Ee]\s+\d+', '', text)
    
    # Remove separators
    text = re.sub(r'\s*[;,]\s*', ' ', text)
    
    # Normalize and clean
    text = normalize_description(text)
    
    # Remove location codes at the end
    text = re.sub(r'\s+[A-Z]{3,4}$', '', text)
    
    # Final cleanup
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def detect_payment_type(description: str) -> str:
    """
    Detect payment method from transaction description.
    
    Args:
        description: Transaction description
        
    Returns:
        Payment type: 'interbancario', 'spei', 'internet', 'other'
    """
    if not description:
        return 'other'
    
    desc_upper = description.upper()
    
    if 'PAGO INTERBANCARIO' in desc_upper:
        return 'interbancario'
    if 'SPEI' in desc_upper:
        return 'spei'
    if 'INTERN' in desc_upper and 'PAGO' in desc_upper:
        return 'internet'
    
    return 'other'


def is_interest_charge(description: str) -> bool:
    """
    Check if transaction is an interest charge.
    
    Args:
        description: Transaction description
        
    Returns:
        True if it's an interest charge
    """
    if not description:
        return False
    
    desc_upper = description.upper()
    interest_keywords = ['INTERESES', 'INTERES EFI', 'INTEREST']
    
    return any(keyword in desc_upper for keyword in interest_keywords)


def is_fee_charge(description: str) -> bool:
    """
    Check if transaction is a fee charge.
    
    Args:
        description: Transaction description
        
    Returns:
        True if it's a fee charge
    """
    if not description:
        return False
    
    desc_upper = description.upper()
    fee_keywords = ['COMISION', 'ANUALIDAD', 'PENALIZACION', 'FEE']
    
    return any(keyword in desc_upper for keyword in fee_keywords)


def extract_location_code(description: str) -> Optional[str]:
    """
    Extract location code from description (e.g., 'TLC', 'CDMX').
    
    Args:
        description: Transaction description
        
    Returns:
        Location code or None
    """
    if not description:
        return None
    
    # Look for 3-4 uppercase letters at the end
    match = re.search(r'\b([A-Z]{3,4})$', description.upper())
    if match:
        return match.group(1)
    
    return None
