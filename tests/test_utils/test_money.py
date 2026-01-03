"""Tests for money utility functions."""

import pytest
from fin.utils.money import parse_amount, format_amount_mexican
from decimal import Decimal


def test_parse_amount_basic():
    """Test parsing basic amounts."""
    assert parse_amount("$1,234.56") == Decimal("1234.56")
    assert parse_amount("1234.56") == Decimal("1234.56")
    assert parse_amount("1,234.56") == Decimal("1234.56")


def test_parse_amount_negative():
    """Test parsing negative amounts."""
    assert parse_amount("($100.00)") == Decimal("-100.00")
    assert parse_amount("(100.00)") == Decimal("-100.00")


def test_parse_amount_zero():
    """Test parsing zero and dashes."""
    assert parse_amount("-") == Decimal("0")
    assert parse_amount("") == Decimal("0")
    assert parse_amount("$0.00") == Decimal("0")


def test_parse_amount_invalid():
    """Test parsing invalid amounts."""
    assert parse_amount(None) is None
    assert parse_amount("abc") is None


def test_format_amount_mexican():
    """Test formatting amounts in Mexican format."""
    assert format_amount_mexican(Decimal("1234.56")) == "$1,234.56"
    assert format_amount_mexican(Decimal("0")) == "$0.00"
    assert format_amount_mexican(None) == "$0.00"
