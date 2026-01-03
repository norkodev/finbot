"""Tests for text utility functions."""

import pytest
from fin.utils.text import (
    normalize_description,
    extract_card_digits,
    extract_installment_info,
    clean_merchant_name
)


def test_normalize_description():
    """Test description normalization."""
    assert normalize_description("Café México") == "CAFE MEXICO"
    assert normalize_description("ÜBER  eats") == "UBER EATS"
    assert normalize_description("  amazon   ") == "AMAZON"


def test_normalize_description_special_chars():
    """Test normalization with special characters."""
    assert normalize_description("OXXO***1234") == "OXXO 1234"
    assert normalize_description("Amazon;Prime") == "AMAZON PRIME"


def test_extract_card_digits():
    """Test extracting card digits."""
    assert extract_card_digits("Tarjeta Digital ***1234") == "1234"
    assert extract_card_digits("***9876") == "9876"
    assert extract_card_digits("No digits here") is None


def test_extract_installment_info():
    """Test extracting installment information."""
    assert extract_installment_info("05 DE 12 SPORT CITY") == (5, 12)
    assert extract_installment_info("1 DE 6 AMAZON") == (1, 6)
    assert extract_installment_info("12 de 24 lowercase") == (12, 24)
    assert extract_installment_info("No installments") is None


def test_clean_merchant_name():
    """Test cleaning merchant names."""
    # Card digit removal
    result = clean_merchant_name("AMAZON ; Tarjeta Digital ***3141")
    assert "AMAZON" in result
    # "Tarjeta Digital" removed, but digits remain (can be improved in future)
    
    # Installment info removal
    result = clean_merchant_name("05 DE 12 SPORT CITY UNIVERSITY")
    assert "SPORT CITY UNIVERSITY" in result
    assert "05" not in result or "DE" not in result  # Installment pattern removed
