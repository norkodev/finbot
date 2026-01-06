"""Banamex bank statement extractor."""

from .base import BaseExtractor
from fin.models import Statement, Transaction, InstallmentPlan
from fin.utils import (
    parse_spanish_date,
    parse_amount,
    normalize_description,
)
import re
from decimal import Decimal
from datetime import datetime
import json


class BanamexExtractor(BaseExtractor):
    """Extractor for Banamex bank statements (Clásica, Joy, etc)."""
    
    @property
    def bank_name(self) -> str:
        return "banamex"
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a Banamex statement."""
        try:
            with self._open_pdf(file_path) as pdf:
                # Check first page for Banamex identifier
                first_page = self._extract_text_from_page(pdf.pages[0])
                # Banamex doesn't always say "BANAMEX" explicitly, look for unique patterns
                return ('BANAMEX' in first_page.upper() or 
                        'Número de tarjeta' in first_page and 'Estado de Cuenta Mensual' in first_page)
        except Exception:
            return False
    
    def parse(self, file_path: str):
        """Parse Banamex statement."""
        try:
            with self._open_pdf(file_path) as pdf:
                # Extract full text
                full_text = ""
                for page in pdf.pages:
                    full_text += self._extract_text_from_page(page) + "\n"
                
                # Create statement
                statement = Statement()
                statement.bank = self.bank_name
                statement.source_type = "credit_card"
                statement.source_file = file_path
                
                # Extract summary
                self._extract_summary(full_text, statement)
                
                # Extract transactions and MSI together (Banamex mixes them)
                transactions, installment_plans = self._extract_transactions_and_msi(full_text, statement)
                
                # Store raw data
                statement.raw_data = json.dumps({
                    'file_path': file_path,
                    'extraction_date': datetime.now().isoformat()
                })
                
                return statement, transactions, installment_plans
                
        except Exception as e:
            print(f"Error parsing Banamex statement: {e}")
            import traceback
            traceback.print_exc()
            return None, [], []
    
    def _extract_summary(self, text: str, statement: Statement):
        """Extract summary information from Banamex statement."""
        
        # Extract period dates
        # Format: "Periodo: 21-nov-2025 al 19-dic-2025"
        period_match = re.search(r'Periodo:\s*(\d{1,2}-[a-z]{3}-\d{4})\s+al\s+(\d{1,2}-[a-z]{3}-\d{4})', text, re.IGNORECASE)
        if period_match:
            statement.period_start = parse_spanish_date(period_match.group(1))
            statement.period_end = parse_spanish_date(period_match.group(2))
        
        # Extract statement date (fecha de corte)
        corte_match = re.search(r'Fecha\s+de\s+corte:\s*(\d{1,2}-[a-z]{3}-\d{4})', text, re.IGNORECASE)
        if corte_match:
            statement.statement_date = parse_spanish_date(corte_match.group(1))
        
        # Extract payment amounts
        # "El pago para no generar intereses $20,607.70"
        no_interest_match = re.search(r'pago\s+para\s+no\s+generar\s+intereses\s*\$?\s*([0-9,]+\.\d{2})', text, re.IGNORECASE)
        if no_interest_match:
            statement.payment_no_interest = parse_amount(no_interest_match.group(1))
        
        # "Pago mínimo" - Multiple patterns
        # Pattern 1: "CLABE Interbancaria Pago mínimo:4 $1,250.00" or "Pago mínimo: $1,250.00"
        # Pattern 2: "El pago mínimo $1,250.00"
        min_payment_match = re.search(r'(?:El\s+)?[Pp]ago\s+m[íi]nimo:?\s*\d*\s*\$?\s*([0-9,]+\.\d{2})', text, re.IGNORECASE)
        if min_payment_match:
            statement.minimum_payment = parse_amount(min_payment_match.group(1))
        
        # Extract due date - Banamex format varies
        # Try to find "Fecha límite" or similar
        due_match = re.search(r'Fecha\s+l[íi]mite.*?(\d{1,2}-[a-z]{3}-\d{4})', text, re.IGNORECASE)
        if due_match:
            statement.due_date = parse_spanish_date(due_match.group(1))
        
        # Extract account number (Número de tarjeta)
        # Format varies, try to get last 4 digits
        account_match = re.search(r'Número\s+de\s+tarjeta:?\s*[\d\s]*(\d{4})', text, re.IGNORECASE)
        if account_match:
            statement.account_number = account_match.group(1)
    
    def _extract_transactions_and_msi(self, text: str, statement: Statement):
        """
        Extract both regular transactions and MSI plans.
        Banamex format mixes them: DD-MMM-YYYY DESCRIPTION $AMOUNT1 $AMOUNT2 $PAYMENT [X de Y]
        """
        transactions = []
        installment_plans = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to match MSI pattern first (has "X de Y")
            # Format: 21-nov-2025 DESCRIPTION $ORIGINAL $PENDING $PAYMENT X de Y
            msi_match = re.match(
                r'(\d{1,2}-[a-z]{3}-\d{4})\s+(.+?)\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+(\d+)\s+de\s+(\d+)',
                line,
                re.IGNORECASE
            )
            
            if msi_match:
                plan = InstallmentPlan()
                plan.statement_id = statement.id
                plan.start_date = parse_spanish_date(msi_match.group(1))
                plan.description = msi_match.group(2).strip()
                plan.original_amount = parse_amount(msi_match.group(3))
                plan.pending_balance = parse_amount(msi_match.group(4))
                plan.monthly_payment = parse_amount(msi_match.group(5))
                plan.current_installment = int(msi_match.group(6))
                plan.total_installments = int(msi_match.group(7))
                plan.has_interest = False  # Assume no interest unless detected
                plan.source_bank = self.bank_name
                plan.plan_type = 'msi'
                plan.status = 'active'
                
                # Calculate end date
                plan.calculate_end_date()
                
                installment_plans.append(plan)
                continue
            
            # Try regular transaction pattern (no "X de Y")
            # Format: DD-MMM-YYYY DESCRIPTION $AMOUNT
            trans_match = re.match(
                r'(\d{1,2}-[a-z]{3}-\d{4})\s+(.+?)\s+[\+\-]?\s*\$\s*([0-9,]+\.\d{2})',
                line,
                re.IGNORECASE
            )
            
            if trans_match:
                description = trans_match.group(2).strip()
                
                # Skip if it looks like header or summary line
                if any(keyword in description.upper() for keyword in ['ORDINARIOS', 'MORATORIOS', 'SALDO', 'TOTAL']):
                    continue
                
                trans = Transaction()
                trans.statement_id = statement.id
                trans.date = parse_spanish_date(trans_match.group(1))
                trans.description = description
                trans.description_normalized = normalize_description(description)
                trans.amount = parse_amount(trans_match.group(3))
                
                # Determine transaction type
                desc_upper = description.upper()
                if 'PAGO' in desc_upper:
                    trans.transaction_type = 'payment'
                    trans.amount = -trans.amount  # Payments are negative
                elif 'INTERES' in desc_upper:
                    trans.transaction_type = 'interest'
                    trans.has_interest = True
                elif 'COMISION' in desc_upper or 'ANUALIDAD' in desc_upper:
                    trans.transaction_type = 'fee'
                else:
                    trans.transaction_type = 'expense'
                
                transactions.append(trans)
        
        return transactions, installment_plans
