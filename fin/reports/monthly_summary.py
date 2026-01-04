"""Generate monthly financial summary reports."""

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Tuple
import calendar

from fin.models import Transaction, Statement


def generate_monthly_summary(
    session: Session,
    year: int,
    month: int
) -> str:
    """
    Generate monthly financial summary in markdown format.
    
    Args:
        session: Database session
        year: Year (e.g., 2025)
        month: Month (1-12)
    
    Returns:
        Markdown formatted report
    """
    # Get month name in Spanish
    month_names = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    month_name = month_names[month - 1]
    
    # Query all transactions for the month
    transactions = session.query(Transaction).filter(
        extract('year', Transaction.date) == year,
        extract('month', Transaction.date) == month
    ).all()
    
    if not transactions:
        return f"# Resumen Financiero - {month_name} {year}\n\n*No hay transacciones para este mes.*"
    
    # Calculate totals
    totals = _calculate_totals(transactions)
    
    # Get category breakdown
    categories = _get_category_breakdown(transactions)
    
    # Get financial costs
    costs = _calculate_financial_costs(transactions)
    
    # Compare with previous month
    comparison = _compare_previous_month(session, year, month)
    
    # Build markdown report
    report = _build_markdown_report(
        year, month, month_name,
        totals, categories, costs, comparison
    )
    
    return report


def _calculate_totals(transactions: List[Transaction]) -> Dict[str, Decimal]:
    """Calculate total income, expenses, and savings."""
    income = Decimal('0')
    expenses = Decimal('0')
    
    for trans in transactions:
        amount = abs(Decimal(str(trans.amount)))
        
        if trans.transaction_type in ['payment', 'income']:
            income += amount
        elif trans.transaction_type in ['expense', 'fee', 'interest']:
            expenses += amount
    
    savings = income - expenses
    savings_rate = (savings / income * 100) if income > 0 else Decimal('0')
    
    return {
        'income': income,
        'expenses': expenses,
        'savings': savings,
        'savings_rate': savings_rate
    }


def _get_category_breakdown(
    transactions: List[Transaction]
) -> List[Tuple[str, Decimal, float]]:
    """
    Get top 5 spending categories.
    
    Returns list of (category, amount, percentage).
    """
    from collections import defaultdict
    
    category_totals = defaultdict(Decimal)
    total_expenses = Decimal('0')
    
    for trans in transactions:
        if trans.transaction_type in ['expense']:
            amount = abs(Decimal(str(trans.amount)))
            category = trans.category or 'Sin categoría'
            category_totals[category] += amount
            total_expenses += amount
    
    # Sort by amount and get top 5
    sorted_categories = sorted(
        category_totals.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Calculate percentages
    result = []
    for category, amount in sorted_categories:
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        result.append((category, amount, float(percentage)))
    
    return result


def _calculate_financial_costs(transactions: List[Transaction]) -> Dict[str, Decimal]:
    """Calculate interest and fees paid."""
    interests = Decimal('0')
    fees = Decimal('0')
    
    for trans in transactions:
        amount = abs(Decimal(str(trans.amount)))
        
        if trans.transaction_type == 'interest':
            interests += amount
        elif trans.transaction_type == 'fee':
            fees += amount
        elif 'INTERES' in (trans.description or '').upper():
            interests += amount
        elif 'COMISION' in (trans.description or '').upper():
            fees += amount
    
    return {
        'interests': interests,
        'fees': fees,
        'total': interests + fees
    }


def _compare_previous_month(
    session: Session,
    year: int,
    month: int
) -> Dict[str, any]:
    """Compare with previous month."""
    # Calculate previous month/year
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    # Query previous month transactions
    prev_transactions = session.query(Transaction).filter(
        extract('year', Transaction.date) == prev_year,
        extract('month', Transaction.date) == prev_month
    ).all()
    
    if not prev_transactions:
        return None
    
    # Calculate previous totals
    prev_totals = _calculate_totals(prev_transactions)
    
    # Calculate deltas
    current_expenses = _calculate_totals(
        session.query(Transaction).filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month
        ).all()
    )['expenses']
    
    prev_expenses = prev_totals['expenses']
    
    delta_amount = current_expenses - prev_expenses
    delta_pct = (delta_amount / prev_expenses * 100) if prev_expenses > 0 else Decimal('0')
    
    # Find category with biggest increase
    # (simplified - would need category comparison)
    
    month_names = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    
    return {
        'prev_month_name': month_names[prev_month - 1],
        'delta_amount': delta_amount,
        'delta_pct': float(delta_pct),
        'direction': 'aumento' if delta_amount > 0 else 'reducción'
    }


def _build_markdown_report(
    year: int,
    month: int,
    month_name: str,
    totals: Dict,
    categories: List,
    costs: Dict,
    comparison: Dict
) -> str:
    """Build final markdown report."""
    
    lines = [
        f"# Resumen Financiero - {month_name} {year}",
        "",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Totales",
        f"- **Ingresos**: ${totals['income']:,.2f}",
        f"- **Gastos**: ${totals['expenses']:,.2f}",
        f"- **Ahorro**: ${totals['savings']:,.2f} ({totals['savings_rate']:.1f}%)",
        "",
        "## Gastos por Categoría",
    ]
    
    for i, (category, amount, pct) in enumerate(categories, 1):
        lines.append(f"{i}. **{category}**: ${amount:,.2f} ({pct:.1f}%)")
    
    lines.extend([
        "",
        "## Costo de Deuda",
        f"- Intereses: ${costs['interests']:,.2f}",
        f"- Comisiones: ${costs['fees']:,.2f}",
        f"- **Total**: ${costs['total']:,.2f}",
    ])
    
    if comparison:
        lines.extend([
            "",
            f"## Comparación vs {comparison['prev_month_name']}",
            f"- Gastos: {comparison['direction']} de {abs(comparison['delta_pct']):.1f}% (${abs(comparison['delta_amount']):,.2f})",
        ])
    
    return "\n".join(lines)
