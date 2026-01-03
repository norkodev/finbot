"""Extractors for bank statement parsing."""

from .base import BaseExtractor
from .bbva import BBVAExtractor
from .hsbc import HSBCExtractor
from .banamex import BanamexExtractor
from .banorte import BanorteExtractor
from .detector import BankDetector

__all__ = [
    'BaseExtractor',
    'BBVAExtractor',
    'HSBCExtractor',
    'BanamexExtractor',
    'BanorteExtractor',
    'BankDetector',
]
