"""Tests for database models."""

import pytest
from fin.models import Statement, Transaction, InstallmentPlan, Merchant
from decimal import Decimal
from datetime import date


def test_statement_creation(db_session, sample_statement):
    """Test creating a statement."""
    db_session.add(sample_statement)
    db_session.commit()
    
    # Query it back
    queried = db_session.query(Statement).first()
    assert queried is not None
    assert queried.bank == "bbva"
    assert queried.account_number == "1234"
    assert queried.current_balance == Decimal("8500.00")


def test_transaction_creation(db_session, sample_statement, sample_transaction):
    """Test creating a transaction."""
    db_session.add(sample_statement)
    db_session.commit()
    
    sample_transaction.statement_id = sample_statement.id
    db_session.add(sample_transaction)
    db_session.commit()
    
    # Query it back
    queried = db_session.query(Transaction).first()
    assert queried is not None
    assert queried.description == "AMAZON MEXICO"
    assert queried.amount == Decimal("1234.56")


def test_installment_plan_creation(db_session, sample_statement, sample_installment_plan):
    """Test creating an installment plan."""
    db_session.add(sample_statement)
    db_session.commit()
    
    sample_installment_plan.statement_id = sample_statement.id
    db_session.add(sample_installment_plan)
    db_session.commit()
    
    # Query it back
    queried = db_session.query(InstallmentPlan).first()
    assert queried is not None
    assert queried.description == "SPORT CITY UNIVERSITY"
    assert queried.current_installment == 5
    assert queried.total_installments == 12


def test_installment_plan_end_date_calculation(db_session, sample_installment_plan):
    """Test end date calculation for installment plan."""
    sample_installment_plan.start_date = date(2025, 1, 1)
    sample_installment_plan.total_installments = 12
    sample_installment_plan.calculate_end_date()
    
    assert sample_installment_plan.end_date_calculated == date(2026, 1, 1)


def test_statement_transaction_relationship(db_session, sample_statement, sample_transaction):
    """Test relationship between statement and transactions."""
    db_session.add(sample_statement)
    db_session.commit()
    
    sample_transaction.statement_id = sample_statement.id
    db_session.add(sample_transaction)
    db_session.commit()
    
    # Access relationship
    statement = db_session.query(Statement).first()
    assert len(statement.transactions) == 1
    assert statement.transactions[0].description == "AMAZON MEXICO"
