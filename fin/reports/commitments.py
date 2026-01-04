"""Generate commitments report (MSI + subscriptions)."""

from sqlalchemy.orm import Session
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import List, Dict

from fin.models import InstallmentPlan
from fin.analysis.subscriptions import get_active_subscriptions


def generate_commitments_report(session: Session) -> str:
    """
    Generate future financial commitments report.
    
    Includes active MSI and recurring subscriptions.
    
    Args:
        session: Database session
    
    Returns:
        Markdown formatted report
    """
    # Get active MSI
    active_msi = session.query(InstallmentPlan).filter(
        InstallmentPlan.status == 'active',
        InstallmentPlan.pending_balance > 0
    ).all()
    
    # Get active subscriptions
    subscriptions = get_active_subscriptions(session, months_back=3)
    
    # Group MSI by end date
    msi_by_month = _group_msi_by_end_date(active_msi)
    
    # Calculate totals
    total_msi_monthly = sum(
        float(plan.monthly_payment) for plan in active_msi if plan.monthly_payment
    )
    total_subs_monthly = sum(
        float(sub['average_amount']) for sub in subscriptions
    )
    total_monthly = total_msi_monthly + total_subs_monthly
    
    # Build markdown
    report = _build_commitments_markdown(
        active_msi,
        msi_by_month,
        subscriptions,
        total_monthly,
        total_msi_monthly,
        total_subs_monthly
    )
    
    return report


def _group_msi_by_end_date(
    plans: List[InstallmentPlan]
) -> Dict[str, List[InstallmentPlan]]:
    """Group MSI plans by their end month."""
    from collections import defaultdict
    
    grouped = defaultdict(list)
    
    for plan in plans:
        if plan.end_date_calculated:
            month_key = plan.end_date_calculated.strftime('%Y-%m')
            grouped[month_key].append(plan)
    
    # Sort by month
    return dict(sorted(grouped.items()))


def _build_commitments_markdown(
    all_msi: List,
    msi_by_month: Dict,
    subscriptions: List,
    total_monthly: float,
    total_msi: float,
    total_subs: float
) -> str:
    """Build markdown report."""
    
    lines = [
        "# Compromisos Financieros",
        "",
        f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Resumen",
        f"- **Total comprometido mensual**: ${total_monthly:,.2f}",
        f"- MSI activos: {len(all_msi)} planes (${total_msi:,.2f}/mes)",
        f"- Suscripciones: {len(subscriptions)} servicios (${total_subs:,.2f}/mes)",
        "",
    ]
    
    if msi_by_month:
        lines.append("## MSI por Fecha de Término")
        lines.append("")
        
        month_names = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        
        for month_key, plans in msi_by_month.items():
            year, month = month_key.split('-')
            month_name = month_names.get(month, month)
            
            lines.append(f"### Terminan en {month_name} {year}")
            lines.append("")
            
            total_freed = Decimal('0')
            
            for plan in plans:
                monthly = plan.monthly_payment or Decimal('0')
                current = plan.current_installment or 0
                total = plan.total_installments or 0
                
                status = "Termina" if current >= total - 1 else f"{current} de {total}"
                
                lines.append(
                    f"- **{plan.description}**: ${monthly:,.2f}/mes ({status})"
                )
                
                if current >= total - 1:
                    total_freed += monthly
            
            if total_freed > 0:
                lines.append(f"  → Liberarás **${total_freed:,.2f}/mes**")
            
            lines.append("")
    
    if subscriptions:
        lines.append("## Suscripciones Activas")
        lines.append("")
        
        for sub in subscriptions:
            marker = "⭐" if sub['is_known_subscription'] else "•"
            lines.append(
                f"{marker} **{sub['merchant_name']}**: ${sub['average_amount']:,.2f}/mes"
            )
        
        lines.append("")
        lines.append(f"**Total Suscripciones**: ${total_subs:,.2f}/mes")
    
    return "\n".join(lines)
