"""Base extractor class for bank statement parsers."""

from abc import ABC, abstractmethod
from typing import Optional
import pdfplumber


class BaseExtractor(ABC):
    """Abstract base class for bank statement extractors."""
    
    @property
    @abstractmethod
    def bank_name(self) -> str:
        """Return the name of the bank this extractor handles."""
        pass
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """
        Determine if this extractor can parse the given file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            True if this extractor can handle the file
        """
        pass
    
    @abstractmethod
    def parse(self, file_path: str):
        """
        Parse the bank statement and return a Statement object.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Statement object or None if parsing fails
        """
        pass
    
    def _open_pdf(self, file_path: str):
        """
        Helper method to open PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            pdfplumber.PDF object
        """
        return pdfplumber.open(file_path)
    
    def _extract_text_from_page(self, page) -> str:
        """
        Helper method to extract text from a page.
        
        Args:
            page: pdfplumber page object
            
        Returns:
            Text content
        """
        return page.extract_text() or ""
    
    def _find_text_in_pdf(self, pdf, search_text: str) -> bool:
        """
        Helper method to search for text in PDF.
        
        Args:
            pdf: pdfplumber.PDF object
            search_text: Text to search for
            
        Returns:
            True if text is found
        """
        for page in pdf.pages:
            text = self._extract_text_from_page(page)
            if search_text.upper() in text.upper():
                return True
        return False
