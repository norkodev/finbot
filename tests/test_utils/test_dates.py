"""Tests for date utility functions."""

import pytest
from fin.utils.dates import parse_spanish_date, parse_date_range, format_date_mexican
from datetime import datetime


def test_parse_spanish_date():
    """Test parsing Spanish dates."""
    assert parse_spanish_date("15-DIC-2025") == datetime(2025, 12, 15)
    assert parse_spanish_date("01-ENE-2026") == datetime(2026, 1, 1)
    assert parse_spanish_date("31-DIC-2025") == datetime(2025, 12, 31)


def test_parse_spanish_date_invalid():
    """Test parsing invalid dates."""
    assert parse_spanish_date(None) is None
    assert parse_spanish_date("") is None
    assert parse_spanish_date("invalid") is None


def test_parse_date_range():
    """Test parsing date ranges."""
    start, end = parse_date_range("01-DIC-2025 AL 31-DIC-2025")
    assert start == datetime(2025, 12, 1)
    assert end == datetime(2025, 12, 31)


def test_parse_date_range_invalid():
    """Test parsing invalid date ranges."""
    start, end = parse_date_range("")
    assert start is None
    assert end is None


def test_format_date_mexican():
    """Test formatting dates in Mexican format."""
    date = datetime(2025, 12, 15)
    assert format_date_mexican(date) == "15/12/2025"
