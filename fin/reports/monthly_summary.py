"""Generate monthly financial summary reports."""

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Tuple
import calendar

from fin.models import Transaction, Statement, InstallmentPlan


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
    
    # Generate executive summary
    exec_summary = _generate_executive_summary(totals, categories, comparison)
    
    # Generate recommendations
    recommendations = _generate_recommendations(session, totals, categories, costs)
    
    # Build markdown report
    report = _build_markdown_report(
        year, month, month_name,
        totals, categories, costs, comparison,
        exec_summary, recommendations
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


def _generate_executive_summary(
    totals: Dict,
    categories: List,
    comparison: Dict
) -> List[str]:
    """Generate executive summary highlights."""
    highlights = []
    
    # Savings status
    savings = totals['savings']
    savings_rate = totals['savings_rate']
    
    if savings > 0:
        arrow = "↑" if comparison and comparison['delta_amount'] < 0 else ""
        highlights.append(f"✅ Ahorro: ${savings:,.2f} ({savings_rate:.1f}%) {arrow}")
    elif savings < 0:
        highlights.append(f"⚠️  Déficit: ${abs(savings):,.2f} ({abs(savings_rate):.1f}%)")
    else:
        highlights.append("⚠️  Ahorro: $0.00 (balance cero)")
    
    # Dominant category alert
    if categories and len(categories) > 0:
        top_category, top_amount, top_pct = categories[0]
        if top_pct > 30:
            highlights.append(f"⚠️  Categoría dominante: {top_category} ({top_pct:.0f}%)")
    
    # Opportunity (if high expenses vs income)
    expense_rate = (totals['expenses'] / totals['income'] * 100) if totals['income'] > 0 else 0
    if expense_rate > 85:
        highlights.append(f"⚠️  Alta tasa de gasto: {expense_rate:.0f}% de ingresos")
    
    return highlights


def _generate_recommendations(
    session: Session,
    totals: Dict,
    categories: List,
    costs: Dict
) -> List[str]:
    """Generate actionable recommendations (max 3)."""
    recommendations = []
    
    # High debt costs
    if costs['total'] > 1000:
        recommendations.append(
            f"💰 Reducir deuda: pagaste ${costs['total']:,.2f} en intereses+comisiones"
        )
    
    # Check subscriptions
    try:
        from fin.analysis.subscriptions import get_active_subscriptions
        subs = get_active_subscriptions(session, months_back=3)
        if len(subs) > 5:
            total_subs = sum(s['average_amount'] for s in subs)
            recommendations.append(
                f"📅 Revisar suscripciones: {len(subs)} activas (${total_subs:,.2f}/mes)"
            )
    except:
        pass  # Subscription module not available
    
    # Gastos hormiga alert
    hormiga_cat = next(
        (c for c in categories if 'hormiga' in c[0].lower()),
        None
    )
    if hormiga_cat and hormiga_cat[1] > 500:
        recommendations.append(
            f"🛒 Reducir gastos hormiga: ${hormiga_cat[1]:,.2f} en {hormiga_cat[0]}"
        )
    
    # MSI ending soon
    ending_soon = _check_ending_msi(session)
    if ending_soon:
        total_free = sum(m['monthly_payment'] for m in ending_soon)
        recommendations.append(
            f"📆 {len(ending_soon)} MSI terminan pronto (liberarás ${total_free:,.2f}/mes)"
        )
    
    return recommendations[:3]  # Max 3


def _check_ending_msi(session: Session) -> List[Dict]:
    """Check for MSI ending in next 3 months."""
    from datetime import timedelta
    
    try:
        plans = session.query(InstallmentPlan).filter(
            InstallmentPlan.status == 'active'
        ).all()
        
        ending_soon = []
        cutoff = datetime.now().date() + timedelta(days=90)  # 3 months
        
        for plan in plans:
            if plan.end_date_calculated and plan.end_date_calculated <= cutoff:
                ending_soon.append({
                    'description': plan.description,
                    'monthly_payment': float(plan.monthly_payment) if plan.monthly_payment else 0
                })
        
        return ending_soon
    except:
        return []


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
        f"# 📊 Reporte Financiero - {month_name} {year}",
        "",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ""
    ]
    
    # Executive Summary
    if exec_summary:
        lines.extend([
            "## Resumen Ejecutivo",
            ""
        ])
        for highlight in exec_summary:
            lines.append(highlight)
        lines.append("")
    
    lines.extend([
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
    
    # Recommendations
    if recommendations:
        lines.extend([
            "",
            "## Recomendaciones",
            ""
        ])
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
    
    return "\n".join(lines)
