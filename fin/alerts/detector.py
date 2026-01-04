"""Alert detection and anomaly analysis."""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta
from decimal import Decimal
import statistics

from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from fin.models import Transaction, InstallmentPlan


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Financial alert data class."""
    level: AlertLevel
    title: str
    description: str
    category: str
    value: float
    threshold: float
    created_at: datetime
    
    def __str__(self):
        """String representation with emoji."""
        emoji_map = {
            AlertLevel.INFO: "💡",
            AlertLevel.WARNING: "⚠️ ",
            AlertLevel.CRITICAL: "🚨"
        }
        emoji = emoji_map[self.level]
        level_str = self.level.value.upper()
        return f"{emoji} [{level_str}] {self.title}: {self.description}"


class AlertDetector:
    """Detect financial alerts and anomalies."""
    
    def __init__(
        self,
        session: Session,
        config: Dict = None
    ):
        """
        Initialize alert detector.
        
        Args:
            session: Database session
            config: Optional configuration overrides
        """
        self.session = session
        self.config = config or self._default_config()
    
    def _default_config(self) -> Dict:
        """Default alert thresholds."""
        return {
            'gastos_hormiga_weekly': 500,
            'category_dominance_pct': 30,
            'unusual_spending_sigma': 2.0,
            'msi_ending_soon_months': 3
        }
    
    def detect_all(
        self,
        year: int,
        month: int
    ) -> List[Alert]:
        """
        Run all detectors and return alerts.
        
        Args:
            year: Year to analyze
            month: Month to analyze
        
        Returns:
            List of alerts sorted by severity
        """
        alerts = []
        
        alerts.extend(self._detect_gastos_hormiga(year, month))
        alerts.extend(self._detect_category_dominance(year, month))
        alerts.extend(self._detect_unusual_spending(year, month))
        alerts.extend(self._detect_fees(year, month))
        alerts.extend(self._detect_ending_msi())
        
        # Sort by level (critical first)
        level_priority = {
            AlertLevel.CRITICAL: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.INFO: 2
        }
        alerts.sort(key=lambda a: level_priority[a.level])
        
        return alerts
    
    def _detect_gastos_hormiga(self, year: int, month: int) -> List[Alert]:
        """Detect high convenience store spending."""
        start_date = datetime(year, month, 1).date()
        
        # Calculate end date (last day of month)
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        transactions = self.session.query(Transaction).filter(
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.category == 'gastos_hormiga'
        ).all()
        
        if not transactions:
            return []
        
        total = sum(abs(Decimal(str(t.amount))) for t in transactions)
        weekly_avg = float(total) / 4  # ~4 weeks/month
        
        threshold = self.config['gastos_hormiga_weekly']
        
        if weekly_avg > threshold:
            return [Alert(
                level=AlertLevel.WARNING,
                title="Gastos Hormiga Altos",
                description=f"Promedio semanal: ${weekly_avg:.2f} (límite: ${threshold})",
                category="gastos_hormiga",
                value=weekly_avg,
                threshold=threshold,
                created_at=datetime.now()
            )]
        
        return []
    
    def _detect_category_dominance(self, year: int, month: int) -> List[Alert]:
        """Detect if one category dominates spending."""
        from collections import defaultdict
        
        transactions = self.session.query(Transaction).filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month,
            Transaction.transaction_type == 'expense'
        ).all()
        
        if not transactions:
            return []
        
        category_totals = defaultdict(Decimal)
        total_expenses = Decimal('0')
        
        for trans in transactions:
            amount = abs(Decimal(str(trans.amount)))
            category = trans.category or 'Sin categoría'
            category_totals[category] += amount
            total_expenses += amount
        
        if total_expenses == 0:
            return []
        
        # Find top category
        top_category = max(category_totals.items(), key=lambda x: x[1])
        category_name, category_amount = top_category
        
        percentage = float(category_amount / total_expenses * 100)
        threshold = self.config['category_dominance_pct']
        
        if percentage > threshold:
            return [Alert(
                level=AlertLevel.WARNING,
                title="Categoría Dominante",
                description=f"{category_name} representa {percentage:.0f}% del gasto total",
                category=category_name,
                value=percentage,
                threshold=threshold,
                created_at=datetime.now()
            )]
        
        return []
    
    def _detect_unusual_spending(self, year: int, month: int) -> List[Alert]:
        """Detect spending >2 standard deviations from average."""
        # Current month total
        current_total = self.session.query(func.sum(Transaction.amount)).filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month,
            Transaction.transaction_type == 'expense'
        ).scalar() or 0
        
        current_total = abs(float(current_total))
        
        # 6-month average
        monthly_totals = []
        for i in range(1, 7):
            prev_month = month - i
            prev_year = year
            if prev_month <= 0:
                prev_month += 12
                prev_year -= 1
            
            total = self.session.query(func.sum(Transaction.amount)).filter(
                extract('year', Transaction.date) == prev_year,
                extract('month', Transaction.date) == prev_month,
                Transaction.transaction_type == 'expense'
            ).scalar() or 0
            
            monthly_totals.append(abs(float(total)))
        
        if len(monthly_totals) < 3:
            return []  # Not enough data
        
        avg = statistics.mean(monthly_totals)
        stdev = statistics.stdev(monthly_totals) if len(monthly_totals) > 1 else 0
        
        sigma = self.config['unusual_spending_sigma']
        threshold = avg + (sigma * stdev)
        
        if current_total > threshold and stdev > 0:
            pct_increase = ((current_total - avg) / avg * 100) if avg > 0 else 0
            return [Alert(
                level=AlertLevel.CRITICAL,
                title="Gasto Inusualmente Alto",
                description=f"${current_total:,.0f} vs promedio ${avg:,.0f} (+{pct_increase:.0f}%)",
                category="total",
                value=current_total,
                threshold=threshold,
                created_at=datetime.now()
            )]
        
        return []
    
    def _detect_fees(self, year: int, month: int) -> List[Alert]:
        """Detect fees and penalties."""
        fees = self.session.query(Transaction).filter(
            extract('year', Transaction.date) == year,
            extract('month', Transaction.date) == month,
            Transaction.transaction_type == 'fee'
        ).all()
        
        if not fees:
            return []
        
        total_fees = sum(abs(Decimal(str(f.amount))) for f in fees)
        
        if total_fees > 0:
            return [Alert(
                level=AlertLevel.WARNING,
                title="Comisiones Cobradas",
                description=f"${float(total_fees):,.2f} en comisiones este mes",
                category="fees",
                value=float(total_fees),
                threshold=0,
                created_at=datetime.now()
            )]
        
        return []
    
    def _detect_ending_msi(self) -> List[Alert]:
        """Detect MSI ending soon."""
        from datetime import timedelta
        
        plans = self.session.query(InstallmentPlan).filter(
            InstallmentPlan.status == 'active'
        ).all()
        
        if not plans:
            return []
        
        ending_soon = []
        cutoff = datetime.now().date() + timedelta(days=self.config['msi_ending_soon_months'] * 30)
        
        for plan in plans:
            if plan.end_date_calculated and plan.end_date_calculated <= cutoff:
                payment = float(plan.monthly_payment) if plan.monthly_payment else 0
                ending_soon.append({
                    'description': plan.description,
                    'monthly_payment': payment
                })
        
        if ending_soon:
            total_to_free = sum(p['monthly_payment'] for p in ending_soon)
            
            return [Alert(
                level=AlertLevel.INFO,
                title="MSI Próximos a Terminar",
                description=f"{len(ending_soon)} planes terminan pronto (liberarás ${total_to_free:,.2f}/mes)",
                category="msi",
                value=total_to_free,
                threshold=0,
                created_at=datetime.now()
            )]
        
        return []
