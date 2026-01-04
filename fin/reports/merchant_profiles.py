"""Generate merchant spending profiles."""

from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Tuple

from fin.models import Merchant, Transaction


def generate_merchant_profiles(
    session: Session,
    min_transactions: int = 3,
    months_back: int = 6
) -> List[Tuple[str, str]]:
    """
    Generate merchant spending profiles.
    
    Args:
        session: Database session
        min_transactions: Minimum transactions to generate profile
        months_back: How many months of history to analyze
    
    Returns:
        List of (merchant_name, markdown_content) tuples
    """
    # Calculate cutoff date
    cutoff_date = datetime.now().date() - timedelta(days=months_back * 30)
    
    # Query merchants with enough transactions
    merchants = session.query(Merchant).join(Transaction).filter(
        Transaction.date >= cutoff_date
    ).group_by(Merchant.id).having(
        func.count(Transaction.id) >= min_transactions
    ).all()
    
    profiles = []
    
    for merchant in merchants:
        # Get transactions for this merchant
        transactions = session.query(Transaction).filter(
            Transaction.merchant_id == merchant.id,
            Transaction.date >= cutoff_date,
            Transaction.transaction_type == 'expense'
        ).order_by(Transaction.date.desc()).all()
        
        if not transactions:
            continue
        
        # Calculate stats
        stats = _calculate_merchant_stats(transactions, months_back)
        
        # Build markdown
        markdown = _build_merchant_markdown(merchant, stats, transactions[:5])
        
        profiles.append((merchant.normalized_name, markdown))
    
    return profiles


def _calculate_merchant_stats(
    transactions: List[Transaction],
    months_back: int
) -> dict:
    """Calculate merchant statistics."""
    total_spent = sum(abs(Decimal(str(t.amount))) for t in transactions)
    count = len(transactions)
    avg_ticket = total_spent / count if count > 0 else Decimal('0')
    frequency_per_month = count / months_back if months_back > 0 else 0
    
    return {
        'total_spent': total_spent,
        'count': count,
        'avg_ticket': avg_ticket,
        'frequency_per_month': frequency_per_month
    }


def _build_merchant_markdown(
    merchant: Merchant,
    stats: dict,
    recent_transactions: List[Transaction]
) -> str:
    """Build merchant profile markdown."""
    
    lines = [
        f"# Perfil: {merchant.name}",
        "",
        "## Clasificación",
        f"- Categoría: {merchant.category or 'Sin clasificar'}",
        f"- Subcategoría: {merchant.subcategory or 'N/A'}",
        "",
        "## Estadísticas (últimos 6 meses)",
        f"- Total gastado: ${stats['total_spent']:,.2f}",
        f"- Número de visitas: {stats['count']}",
        f"- Ticket promedio: ${stats['avg_ticket']:,.2f}",
        f"- Frecuencia: {stats['frequency_per_month']:.1f} veces/mes",
        "",
    ]
    
    if recent_transactions:
        lines.append("## Últimas Transacciones")
        for trans in recent_transactions:
            amount = abs(Decimal(str(trans.amount)))
            lines.append(f"- {trans.date.strftime('%d-%b-%Y')}: ${amount:,.2f}")
        lines.append("")
    
    return "\n".join(lines)
