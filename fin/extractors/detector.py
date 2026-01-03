"""Bank detector for automatic bank identification."""

from .bbva import BBVAExtractor
from .hsbc import HSBCExtractor
from .banamex import BanamexExtractor
from typing import Optional


class BankDetector:
    """Automatically detect which bank a statement is from."""
    
    def __init__(self):
        """Initialize detector with all available extractors."""
        self.extractors = [
            HSBCExtractor(),
            BanamexExtractor(),
            BBVAExtractor(),
        ]
    
    def detect(self, file_path: str) -> Optional:
        """
        Detect which extractor can parse the given file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Appropriate extractor instance or None
        """
        for extractor in self.extractors:
            if extractor.can_parse(file_path):
                return extractor
        
        return None
    
    def get_bank_name(self, file_path: str) -> Optional[str]:
        """
        Get the name of the bank for the given file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Bank name or None
        """
        extractor = self.detect(file_path)
        if extractor:
            return extractor.bank_name
        return None
