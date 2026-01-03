"""Utility functions for date parsing and manipulation."""

from datetime import datetime
from typing import Optional
from dateutil import parser as date_parser
import re


# Spanish month names mapping
SPANISH_MONTHS = {
    'ENE': 'JAN', 'FEB': 'FEB', 'MAR': 'MAR', 'ABR': 'APR',
    'MAY': 'MAY', 'JUN': 'JUN', 'JUL': 'JUL', 'AGO': 'AUG',
    'SEP': 'SEP', 'OCT': 'OCT', 'NOV': 'NOV', 'DIC': 'DEC'
}


def parse_spanish_date(text: str) -> Optional[datetime]:
    """
    Parse a date in Spanish format (e.g., '15-DIC-2025').
    
    Args:
        text: Date string in Spanish format
        
    Returns:
        datetime object or None if parsing fails
    """
    if not text or not isinstance(text, str):
        return None
    
    text = text.strip().upper()
    
    # Replace Spanish month names with English equivalents
    for es, en in SPANISH_MONTHS.items():
        text = text.replace(es, en)
    
    try:
        return date_parser.parse(text, dayfirst=True)
    except (ValueError, TypeError):
        return None


def parse_date_range(text: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse a date range (e.g., '01-DIC-2025 AL 31-DIC-2025').
    
    Args:
        text: Date range string
        
    Returns:
        Tuple of (start_date, end_date) or (None, None) if parsing fails
    """
    if not text:
        return None, None
    
    # Try to split by common separators
    separators = [' AL ', ' A ', ' - ', ' TO ']
    
    for sep in separators:
        if sep in text.upper():
            parts = text.upper().split(sep)
            if len(parts) == 2:
                start = parse_spanish_date(parts[0].strip())
                end = parse_spanish_date(parts[1].strip())
                return start, end
    
    return None, None


def format_date_mexican(date: datetime) -> str:
    """
    Format date in Mexican format (DD/MM/YYYY).
    
    Args:
        date: datetime object
        
    Returns:
        Formatted date string
    """
    if not date:
        return ""
    
    return date.strftime("%d/%m/%Y")
