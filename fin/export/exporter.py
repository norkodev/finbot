"""Export financial data to various formats."""

import csv
import json
from typing import List, Dict, Optional
from datetime import datetime, date
from io import StringIO

from sqlalchemy.orm import Session
from sqlalchemy import func

from fin.models import Transaction, InstallmentPlan, Merchant


class DataExporter:
    """Export financial data to CSV or JSON."""
    
    def __init__(self, session: Session):
        """
        Initialize exporter.
        
        Args:
            session: Database session
        """
        self.session = session
    
    def export_transactions(
        self,
        format: str = 'csv',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category: Optional[str] = None,
        bank: Optional[str] = None,
        merchant: Optional[str] = None
    ) -> str:
        """
        Export transactions with optional filters.
        
        Args:
            format: 'csv' or 'json'
            start_date: Filter from this date
            end_date: Filter to this date
            category: Filter by category
            bank: Filter by bank
            merchant: Filter by merchant name
        
        Returns:
            Formatted string (CSV or JSON)
        """
        # Build query
        query = self.session.query(Transaction)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if category:
            query = query.filter(Transaction.category == category)
        if bank:
            query = query.join(Transaction.statement).filter(
                func.lower(Transaction.statement.bank).like(f"%{bank.lower()}%")
            )
        if merchant:
            query = query.join(Transaction.merchant).filter(
                func.lower(Merchant.name).like(f"%{merchant.lower()}%")
            )
        
        transactions = query.order_by(Transaction.date.desc()).all()
        
        if format == 'csv':
            return self._to_csv_transactions(transactions)
        elif format == 'json':
            return self._to_json_transactions(transactions)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def export_msi(
        self,
        format: str = 'csv',
        status: str = 'active'
    ) -> str:
        """
        Export installment plans.
        
        Args:
            format: 'csv' or 'json'
            status: Filter by status ('active', 'completed', 'all')
        
        Returns:
            Formatted string (CSV or JSON)
        """
        query = self.session.query(InstallmentPlan)
        
        if status != 'all':
            query = query.filter(InstallmentPlan.status == status)
        
        plans = query.order_by(InstallmentPlan.start_date.desc()).all()
        
        if format == 'csv':
            return self._to_csv_msi(plans)
        elif format == 'json':
            return self._to_json_msi(plans)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _to_csv_transactions(self, transactions: List[Transaction]) -> str:
        """Convert transactions to CSV."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'date',
            'description',
            'amount',
            'category',
            'subcategory',
            'merchant',
            'type',
            'bank',
            'card_last_4'
        ])
        
        # Rows
        for t in transactions:
            writer.writerow([
                t.date.isoformat() if t.date else '',
                t.description or '',
                float(t.amount) if t.amount else 0,
                t.category or '',
                t.subcategory or '',
                t.merchant.name if t.merchant else '',
                t.transaction_type or '',
                t.statement.bank if t.statement else '',
                t.statement.card_last_4 if t.statement else ''
            ])
        
        return output.getvalue()
    
    def _to_json_transactions(self, transactions: List[Transaction]) -> str:
        """Convert transactions to JSON."""
        data = []
        
        for t in transactions:
            data.append({
                'date': t.date.isoformat() if t.date else None,
                'description': t.description,
                'amount': float(t.amount) if t.amount else 0,
                'category': t.category,
                'subcategory': t.subcategory,
                'merchant': t.merchant.name if t.merchant else None,
                'merchant_id': str(t.merchant.id) if t.merchant else None,
                'type': t.transaction_type,
                'bank': t.statement.bank if t.statement else None,
                'card_last_4': t.statement.card_last_4 if t.statement else None,
                'installment_info': t.installment_info
            })
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _to_csv_msi(self, plans: List[InstallmentPlan]) -> str:
        """Convert MSI plans to CSV."""
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'description',
            'status',
            'original_amount',
            'monthly_payment',
            'total_installments',
            'paid_installments',
            'pending_balance',
            'start_date',
            'end_date_calculated',
            'interest_rate',
            'bank'
        ])
        
        # Rows
        for p in plans:
            writer.writerow([
                p.description or '',
                p.status or '',
                float(p.original_amount) if p.original_amount else 0,
                float(p.monthly_payment) if p.monthly_payment else 0,
                p.total_installments or 0,
                p.paid_installments or 0,
                float(p.pending_balance) if p.pending_balance else 0,
                p.start_date.isoformat() if p.start_date else '',
                p.end_date_calculated.isoformat() if p.end_date_calculated else '',
                float(p.interest_rate) if p.interest_rate else 0,
                p.statement.bank if p.statement else ''
            ])
        
        return output.getvalue()
    
    def _to_json_msi(self, plans: List[InstallmentPlan]) -> str:
        """Convert MSI plans to JSON."""
        data = []
        
        for p in plans:
            data.append({
                'id': str(p.id),
                'description': p.description,
                'status': p.status,
                'original_amount': float(p.original_amount) if p.original_amount else 0,
                'monthly_payment': float(p.monthly_payment) if p.monthly_payment else 0,
                'total_installments': p.total_installments,
                'paid_installments': p.paid_installments,
                'pending_balance': float(p.pending_balance) if p.pending_balance else 0,
                'start_date': p.start_date.isoformat() if p.start_date else None,
                'end_date_calculated': p.end_date_calculated.isoformat() if p.end_date_calculated else None,
                'interest_rate': float(p.interest_rate) if p.interest_rate else None,
                'bank': p.statement.bank if p.statement else None
            })
        
        return json.dumps(data, indent=2, ensure_ascii=False)
