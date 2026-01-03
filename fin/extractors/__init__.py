"""Extractors for bank statement parsing."""

from .base import BaseExtractor
from .bbva import BBVAExtractor
from .hsbc import HSBCExtractor
from .detector import BankDetector

__all__ = [
    'BaseExtractor',
    'BBVAExtractor',
    'HSBCExtractor',
    'BankDetector',
]
