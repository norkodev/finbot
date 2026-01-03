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
    
    # Remove location codes (e.g., "TLC", "CDMX")
    # This is optional and may need adjustment
    
    # Collapse spaces again
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()
