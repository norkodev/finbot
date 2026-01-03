"""Pytest configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fin.models import Base, Statement, Transaction, InstallmentPlan, Merchant
from decimal import Decimal
from datetime import datetime, date


@pytest.fixture
def in_memory_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(in_memory_engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_statement():
    """Create a sample statement for testing."""
    statement = Statement()
    statement.bank = "bbva"
    statement.source_type = "credit_card"
    statement.account_number = "1234"
    statement.period_start = date(2025, 12, 1)
    statement.period_end = date(2025, 12, 31)
    statement.statement_date = date(2025, 12, 31)
    statement.due_date = date(2026, 1, 20)
    statement.previous_balance = Decimal("5000.00")
    statement.current_balance = Decimal("8500.00")
    statement.minimum_payment = Decimal("250.00")
    statement.payment_no_interest = Decimal("8500.00")
    statement.credit_limit = Decimal("50000.00")
    statement.available_credit = Decimal("41500.00")
    statement.source_file = "/path/to/test.pdf"
    
    return statement


@pytest.fixture
def sample_transaction(sample_statement):
    """Create a sample transaction for testing."""
    transaction = Transaction()
    transaction.statement_id = sample_statement.id
    transaction.date = date(2025, 12, 15)
    transaction.description = "AMAZON MEXICO"
    transaction.description_normalized = "AMAZON MEXICO"
    transaction.amount = Decimal("1234.56")
    transaction.currency = "MXN"
    transaction.transaction_type = "expense"
    transaction.has_interest = False
    
    return transaction


@pytest.fixture
def sample_installment_plan(sample_statement):
    """Create a sample installment plan for testing."""
    plan = InstallmentPlan()
    plan.statement_id = sample_statement.id
    plan.description = "SPORT CITY UNIVERSITY"
    plan.original_amount = Decimal("12000.00")
    plan.pending_balance = Decimal("7500.00")
    plan.monthly_payment = Decimal("1000.00")
    plan.current_installment = 5
    plan.total_installments = 12
    plan.start_date = date(2025, 8, 1)
    plan.has_interest = False
    plan.interest_rate = Decimal("0.00")
    plan.source_bank = "bbva"
    plan.plan_type = "msi"
    plan.status = "active"
    
    return plan
