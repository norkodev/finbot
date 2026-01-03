"""BBVA bank statement extractor."""

from .base import BaseExtractor
from fin.models import Statement, Transaction, InstallmentPlan
from fin.utils import (
    parse_spanish_date,
    parse_date_range,
    parse_amount,
    normalize_description,
    extract_installment_info,
    clean_merchant_name
)
import re
from decimal import Decimal
from datetime import datetime
import json


class BBVAExtractor(BaseExtractor):
    """Extractor for BBVA bank statements."""
    
    @property
    def bank_name(self) -> str:
        return "bbva"
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a BBVA statement."""
        try:
            with self._open_pdf(file_path) as pdf:
                return self._find_text_in_pdf(pdf, "BBVA")
        except Exception:
            return False
    
    def parse(self, file_path: str):
        """Parse BBVA statement."""
        try:
            with self._open_pdf(file_path) as pdf:
                # Extract full text for easier parsing
                full_text = ""
                for page in pdf.pages:
                    full_text += self._extract_text_from_page(page) + "\n"
                
                # Create statement object
                statement = Statement()
                statement.bank = self.bank_name
                statement.source_type = "credit_card"
                statement.source_file = file_path
                
                # Extract summary information
                self._extract_summary(full_text, statement)
                
                # Extract transactions (will be done separately)
                transactions = []
                transactions.extend(self._extract_regular_transactions(full_text, statement))
                
                # Extract MSI plans
                installment_plans = []
                installment_plans.extend(self._extract_msi_no_interest(full_text, statement))
                installment_plans.extend(self._extract_msi_with_interest(full_text, statement))
                
                # Store raw data
                statement.raw_data = json.dumps({
                    'file_path': file_path,
                    'extraction_date': datetime.now().isoformat()
                })
                
                return statement, transactions, installment_plans
                
        except Exception as e:
            print(f"Error parsing BBVA statement: {e}")
            return None, [], []
    
    def _extract_summary(self, text: str, statement: Statement):
        """Extract summary information from statement."""
        
        # Extract period dates
        period_match = re.search(r'PERIODO.*?(\d{2}-[A-Z]{3}-\d{4}).*?AL.*?(\d{2}-[A-Z]{3}-\d{4})', text, re.IGNORECASE)
        if period_match:
            statement.period_start = parse_spanish_date(period_match.group(1))
            statement.period_end = parse_spanish_date(period_match.group(2))
        
        # Extract statement date (fecha de corte)
        corte_match = re.search(r'FECHA DE CORTE.*?(\d{2}-[A-Z]{3}-\d{4})', text, re.IGNORECASE)
        if corte_match:
            statement.statement_date = parse_spanish_date(corte_match.group(1))
        
        # Extract due date (fecha límite de pago)
        due_match = re.search(r'FECHA LÍMITE DE PAGO.*?(\d{2}-[A-Z]{3}-\d{4})', text, re.IGNORECASE)
        if due_match:
            statement.due_date = parse_spanish_date(due_match.group(1))
        
        # Extract balances
        # Saldo anterior
        prev_balance_match = re.search(r'SALDO ANTERIOR.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if prev_balance_match:
            statement.previous_balance = parse_amount(prev_balance_match.group(1))
        
        # Saldo deudor total
        current_balance_match = re.search(r'SALDO DEUDOR TOTAL.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if current_balance_match:
            statement.current_balance = parse_amount(current_balance_match.group(1))
        
        # Pago mínimo
        min_payment_match = re.search(r'PAGO MÍNIMO.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if min_payment_match:
            statement.minimum_payment = parse_amount(min_payment_match.group(1))
        
        # Pago para no generar intereses
        no_interest_match = re.search(r'PAGO PARA NO GENERAR INTERESES.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if no_interest_match:
            statement.payment_no_interest = parse_amount(no_interest_match.group(1))
        
        # Límite de crédito
        limit_match = re.search(r'LÍMITE DE CRÉDITO.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if limit_match:
            statement.credit_limit = parse_amount(limit_match.group(1))
        
        # Crédito disponible
        available_match = re.search(r'CRÉDITO DISPONIBLE.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if available_match:
            statement.available_credit = parse_amount(available_match.group(1))
        
        # Extract account number (last 4 digits)
        account_match = re.search(r'TARJETA.*?(\d{4})', text)
        if account_match:
            statement.account_number = account_match.group(1)
    
    def _extract_regular_transactions(self, text: str, statement: Statement):
        """Extract regular transactions from statement."""
        transactions = []
        
        # Find the transactions section
        # This is a simplified parser - real implementation would need more robust parsing
        lines = text.split('\n')
        
        in_transactions_section = False
        for line in lines:
            # Check if we're in the transactions section
            if 'OPERACIONES DEL PERIODO' in line.upper() or 'FECHA OPERACION' in line.upper():
                in_transactions_section = True
                continue
            
            # Check if we've left the transactions section
            if in_transactions_section and ('COMPRAS A MESES' in line.upper() or 'RESUMEN' in line.upper()):
                break
            
            if not in_transactions_section:
                continue
            
            # Try to parse transaction line
            # Expected format: DATE  POST_DATE  DESCRIPTION  AMOUNT
            # This is highly simplified - real implementation needs better pattern matching
            trans_match = re.match(
                r'(\d{2}-[A-Z]{3})\s+(\d{2}-[A-Z]{3})\s+(.+?)\s+(\$?\s*[\d,]+\.\d{2})\s*$',
                line,
                re.IGNORECASE
            )
            
            if trans_match:
                date_str = trans_match.group(1)
                post_date_str = trans_match.group(2)
                description = trans_match.group(3).strip()
                amount_str = trans_match.group(4)
                
                # Create transaction
                trans = Transaction()
                trans.statement_id = statement.id
                trans.date = parse_spanish_date(f"{date_str}-{statement.period_end.year if statement.period_end else datetime.now().year}")
                trans.post_date = parse_spanish_date(f"{post_date_str}-{statement.period_end.year if statement.period_end else datetime.now().year}")
                trans.description = description
                trans.description_normalized = normalize_description(description)
                trans.amount = parse_amount(amount_str)
                
                # Determine transaction type
                if 'PAGO' in description.upper():
                    trans.transaction_type = 'payment'
                    trans.amount = -abs(trans.amount) if trans.amount else trans.amount  # Payments are negative
                elif 'INTERES' in description.upper():
                    trans.transaction_type = 'interest'
                    trans.has_interest = True
                elif 'COMISION' in description.upper() or 'ANUALIDAD' in description.upper():
                    trans.transaction_type = 'fee'
                else:
                    trans.transaction_type = 'expense'
                
                # Check if it's an installment payment
                installment_info = extract_installment_info(description)
                if installment_info:
                    trans.is_installment_payment = True
                
                transactions.append(trans)
        
        return transactions
    
    def _extract_msi_no_interest(self, text: str, statement: Statement):
        """Extract MSI without interest plans."""
        plans = []
        
        # Find MSI section
        # Pattern: COMPRAS A MESES SIN INTERESES
        lines = text.split('\n')
        
        in_msi_section = False
        for line in lines:
            if 'COMPRAS A MESES SIN INTERESES' in line.upper():
                in_msi_section = True
                continue
            
            if in_msi_section and ('COMPRAS/DISPOSICIONES A MESES' in line.upper() or 'TOTAL' in line.upper()):
                break
            
            if not in_msi_section:
                continue
            
            # Parse MSI line
            # Expected: DATE  DESCRIPTION  ORIGINAL  PENDING  PAYMENT  INSTALLMENT
            msi_match = re.match(
                r'(\d{2}-[A-Z]{3})\s+(.+?)\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+(\d+)\s+DE\s+(\d+)',
                line,
                re.IGNORECASE
            )
            
            if msi_match:
                plan = InstallmentPlan()
                plan.statement_id = statement.id
                plan.start_date = parse_spanish_date(f"{msi_match.group(1)}-{statement.period_end.year if statement.period_end else datetime.now().year}")
                plan.description = msi_match.group(2).strip()
                plan.original_amount = parse_amount(msi_match.group(3))
                plan.pending_balance = parse_amount(msi_match.group(4))
                plan.monthly_payment = parse_amount(msi_match.group(5))
                plan.current_installment = int(msi_match.group(6))
                plan.total_installments = int(msi_match.group(7))
                plan.has_interest = False
                plan.interest_rate = Decimal('0')
                plan.source_bank = self.bank_name
                plan.plan_type = 'msi'
                plan.status = 'active'
                
                # Calculate end date
                plan.calculate_end_date()
                
                plans.append(plan)
        
        return plans
    
    def _extract_msi_with_interest(self, text: str, statement: Statement):
        """Extract MSI with interest plans."""
        plans = []
        
        # Find MSI with interest section
        # Pattern: COMPRAS/DISPOSICIONES A MESES
        lines = text.split('\n')
        
        in_msi_section = False
        for line in lines:
            if 'COMPRAS/DISPOSICIONES A MESES' in line.upper() and 'SIN INTERESES' not in line.upper():
                in_msi_section = True
                continue
            
            if in_msi_section and 'EFECTIVO INMEDIATO' in line.upper():
                continue  # Special type, handle separately if needed
            
            if in_msi_section and 'TOTAL' in line.upper():
                break
            
            if not in_msi_section:
                continue
            
            # Parse MSI with interest line
            # This is more complex as it includes interest fields
            # Simplified pattern
            msi_match = re.match(
                r'(\d{2}-[A-Z]{3})\s+(.+?)\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})',
                line,
                re.IGNORECASE
            )
            
            if msi_match:
                plan = InstallmentPlan()
                plan.statement_id = statement.id
                plan.start_date = parse_spanish_date(f"{msi_match.group(1)}-{statement.period_end.year if statement.period_end else datetime.now().year}")
                plan.description = msi_match.group(2).strip()
                plan.original_amount = parse_amount(msi_match.group(3))
                plan.pending_balance = parse_amount(msi_match.group(4))
                plan.monthly_payment = parse_amount(msi_match.group(5))
                plan.has_interest = True
                plan.source_bank = self.bank_name
                plan.plan_type = 'msi_with_interest'
                plan.status = 'active'
                
                # Try to extract interest rate from nearby text
                # This would need more sophisticated parsing
                
                plans.append(plan)
        
        return plans
