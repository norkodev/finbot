"""Integration tests for full pipeline."""

import pytest
from pathlib import Path
from datetime import datetime

# Note: These tests require:
# 1. Test fixtures in tests/fixtures/ (anonymized PDFs)
# 2. Ollama running with qwen2.5:7b model


def test_imports():
    """Test that all modules can be imported."""
    from fin.extractors import BankDetector
    from fin.database import init_db, get_session
    from fin.classification.classifier import TransactionClassifier
    from fin.vectorization import IndexPipeline
    from fin.rag import ChatEngine
    from fin.reports import generate_monthly_summary
    from fin.alerts import AlertDetector
    from fin.export import DataExporter
    
    assert True


@pytest.mark.skipif(
    not Path("tests/fixtures/bbva_sample.pdf").exists(),
    reason="No test fixtures available"
)
def test_pdf_extraction(tmp_path):
    """Test PDF extraction for BBVA sample."""
    from fin.extractors import BankDetector
    
    pdf_path = Path("tests/fixtures/bbva_sample.pdf")
    detector = BankDetector()
    
    # Detect bank
    extractor = detector.detect(str(pdf_path))
    assert extractor is not None, "Failed to detect bank"
    
    # Extract
    statement = extractor.extract(str(pdf_path))
    assert statement is not None, "Failed to extract statement"
    assert len(statement.transactions) > 0, "No transactions extracted"
    
    print(f"✓ Extracted {len(statement.transactions)} transactions")


@pytest.mark.skipif(
    not Path("tests/fixtures/bbva_sample.pdf").exists(),
    reason="No test fixtures available"
)
def test_full_pipeline(tmp_path):
    """
    Test complete flow: PDF → DB → Classification → Reports → Index.
    """
    from fin.extractors import BankDetector
    from fin.database import init_db, get_session
    from fin.classification.classifier import TransactionClassifier
    from fin.reports import generate_monthly_summary
    
    # Setup temp database
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    session = get_session(f"sqlite:///{db_path}")
    
    try:
        # 1. Extract PDF
        pdf_path = Path("tests/fixtures/bbva_sample.pdf")
        detector = BankDetector()
        extractor = detector.detect(str(pdf_path))
        statement = extractor.extract(str(pdf_path))
        
        assert statement is not None
        assert len(statement.transactions) > 0
        
        # 2. Save to DB
        session.add(statement)
        session.commit()
        
        # 3. Classify transactions
        classifier = TransactionClassifier(session)
        for trans in statement.transactions:
            classifier.classify(trans)
        session.commit()
        
        # 4. Generate report
        year = statement.period_year
        month = statement.period_month
        report = generate_monthly_summary(session, year, month)
        
        assert report is not None
        assert "Reporte Financiero" in report
        assert "Totales" in report
        
        print("✓ Full pipeline test passed")
        
    finally:
        session.close()


def test_report_generation(tmp_path):
    """Test monthly report generation with mock data."""
    from fin.database import init_db, get_session
    from fin.models import Statement, Transaction, Merchant
    from fin.reports import generate_monthly_summary
    from datetime import date
    from decimal import Decimal
    
    # Setup
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    session = get_session(f"sqlite:///{db_path}")
    
    try:
        # Create mock data
        statement = Statement(
            bank="TEST_BANK",
            period_year=2025,
            period_month=12,
            card_last_4="1234"
        )
        session.add(statement)
        session.flush()
        
        # Add test merchant
        merchant = Merchant(name="TEST_MERCHANT")
        session.add(merchant)
        session.flush()
        
        # Add test transactions
        trans1 = Transaction(
            statement_id=statement.id,
            date=date(2025, 12, 15),
            description="TEST EXPENSE",
            amount=Decimal("-1000.00"),
            transaction_type="expense",
            category="alimentacion",
            merchant_id=merchant.id
        )
        trans2 = Transaction(
            statement_id=statement.id,
            date=date(2025, 12, 20),
            description="TEST INCOME",
            amount=Decimal("5000.00"),
            transaction_type="payment"
        )
        
        session.add_all([trans1, trans2])
        session.commit()
        
        # Generate report
        report = generate_monthly_summary(session, 2025, 12)
        
        assert report is not None
        assert "Diciembre 2025" in report
        assert "Resumen Ejecutivo" in report  # New section
        assert "Totales" in report
        assert "$1,000.00" in report or "$1000" in report
        
        print("✓ Report generation test passed")
        
    finally:
        session.close()


def test_alert_detection(tmp_path):
    """Test alert detection system."""
    from fin.database import init_db, get_session
    from fin.models import Statement, Transaction
    from fin.alerts import AlertDetector, AlertLevel
    from datetime import date
    from decimal import Decimal
    
    # Setup
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    session = get_session(f"sqlite:///{db_path}")
    
    try:
        # Create test data
        statement = Statement(
            bank="TEST_BANK",
            period_year=2025,
            period_month=12,
            card_last_4="1234"
        )
        session.add(statement)
        session.flush()
        
        # Add fee transaction (should trigger alert)
        fee_trans = Transaction(
            statement_id=statement.id,
            date=date(2025, 12, 15),
            description="COMISION",
            amount=Decimal("-50.00"),
            transaction_type="fee"
        )
        session.add(fee_trans)
        session.commit()
        
        # Detect alerts
        detector = AlertDetector(session)
        alerts = detector.detect_all(2025, 12)
        
        # Should have at least the fee alert
        fee_alerts = [a for a in alerts if a.category == "fees"]
        assert len(fee_alerts) > 0, "Fee alert not detected"
        
        print(f"✓ Alert detection test passed ({len(alerts)} alerts)")
        
    finally:
        session.close()


def test_data_export(tmp_path):
    """Test CSV and JSON export."""
    from fin.database import init_db, get_session
    from fin.models import Statement, Transaction
    from fin.export import DataExporter
    from datetime import date
    from decimal import Decimal
    
    # Setup
    db_path = tmp_path / "test.db"
    init_db(f"sqlite:///{db_path}")
    session = get_session(f"sqlite:///{db_path}")
    
    try:
        # Create test data
        statement = Statement(
            bank="TEST_BANK",
            period_year=2025,
            period_month=12,
            card_last_4="1234"
        )
        session.add(statement)
        session.flush()
        
        trans = Transaction(
            statement_id=statement.id,
            date=date(2025, 12, 15),
            description="TEST",
            amount=Decimal("-100.00"),
            transaction_type="expense",
            category="test"
        )
        session.add(trans)
        session.commit()
        
        # Test export
        exporter = DataExporter(session)
        
        # CSV export
        csv_result = exporter.export_transactions(format='csv')
        assert csv_result is not None
        assert "date,description" in csv_result
        assert "TEST" in csv_result
        
        # JSON export
        json_result = exporter.export_transactions(format='json')
        assert json_result is not None
        assert '"description": "TEST"' in json_result
        
        print("✓ Export test passed")
        
    finally:
        session.close()


@pytest.mark.skipif(
    True,  # Skip by default (requires Ollama)
    reason="Requires Ollama running"
)
def test_chat_quality():
    """
    Test chat responses for quality and accuracy.
    
    NOTE: This test requires:
    - Ollama running
    - Real database with indexed documents
    - Set FINBOT_TEST_CHAT=1 environment variable to enable
    """
    import os
    if os.getenv('FINBOT_TEST_CHAT') != '1':
        pytest.skip("Chat testing disabled (set FINBOT_TEST_CHAT=1)")
    
    from fin.rag import ChatEngine
    
    engine = ChatEngine(timeout=120)
    
    # Test questions
    questions = [
        "¿Cuánto gasté en total?",
        "¿Qué MSI tengo activos?",
        "¿Cuáles son mis gastos más altos?"
    ]
    
    for question in questions:
        result = engine.chat(question)
        
        assert result is not None
        assert 'answer' in result
        assert result['answer'] is not None
        assert len(result['answer']) > 20, f"Answer too short for: {question}"
        
        # Check for sources
        if 'sources' in result and len(result['sources']) > 0:
            print(f"✓ '{question}' -> {len(result['sources'])} sources")
        else:
            print(f"⚠ '{question}' -> no sources")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
