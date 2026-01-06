"""Banorte bank statement extractor."""

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


class BanorteExtractor(BaseExtractor):
    """Extractor for Banorte bank statements."""
    
    @property
    def bank_name(self) -> str:
        return "banorte"
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a Banorte statement."""
        try:
            with self._open_pdf(file_path) as pdf:
                # Check first few pages for Banorte identifier
                for i in range(min(3, len(pdf.pages))):
                    text = self._extract_text_from_page(pdf.pages[i])
                    if 'BANORTE' in text.upper() or 'Tarjeta de Crédito Banorte' in text:
                        return True
                return False
        except Exception:
            return False
    
    def parse(self, file_path: str):
        """Parse Banorte statement - Extract 100% of data."""
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
                
                # Extract summary - COMPLETE
                self._extract_summary(full_text, statement)
                
                # Extract transactions - COMPLETE
                transactions = self._extract_transactions(full_text, statement)
                
                # Extract balance transfers (Banorte's MSI equivalent) - COMPLETE
                installment_plans = self._extract_balance_transfers(full_text, statement)
                
                # Store raw data
                statement.raw_data = json.dumps({
                    'file_path': file_path,
                    'extraction_date': datetime.now().isoformat(),
                    'pdf_pages': len(pdf.pages)
                })
                
                return statement, transactions, installment_plans
                
        except Exception as e:
            print(f"Error parsing Banorte statement: {e}")
            import traceback
            traceback.print_exc()
            return None, [], []
    
    def _extract_summary(self, text: str, statement: Statement):
        """Extract COMPLETE summary information from Banorte statement."""
        
        # Extract period dates
        # Format: "Periodo: 15-NOV-2025 al 17-DIC-2025"
        period_match = re.search(r'Periodo:\s*(\d{1,2}-[A-Z]{3}-\d{4})\s+al\s+(\d{1,2}-[A-Z]{3}-\d{4})', text, re.IGNORECASE)
        if period_match:
            statement.period_start = parse_spanish_date(period_match.group(1))
            statement.period_end = parse_spanish_date(period_match.group(2))
        
        # Extract statement date (fecha de corte)
        corte_match = re.search(r'Fecha\s+de\s+corte:\s*(\d{1,2}-[A-Z]{3}-\d{4})', text, re.IGNORECASE)
        if corte_match:
            statement.statement_date = parse_spanish_date(corte_match.group(1))
        
        # Extract due date
        due_match = re.search(r'Fecha\s+límite\s+de\s+pago:.*?(\d{1,2}-[A-Z]{3}-\d{4})', text, re.IGNORECASE)
        if due_match:
            statement.due_date = parse_spanish_date(due_match.group(1))
        
        # Extract payment amounts - ALL variants
        # "Pago para no generar intereses: $14,171.17"
        no_interest_match = re.search(r'Pago\s+para\s+no\s+generar\s+intereses:\s*\$?\s*([0-9,]+\.\d{2})', text, re.IGNORECASE)
        if no_interest_match:
            statement.payment_no_interest = parse_amount(no_interest_match.group(1))
        
        # "Pago mínimo: $4,450.00" or "Pago mínimo:4 $4,450.00" (with reference number)  
        min_payment_match = re.search(r'Pago\s+m[íi]nimo:\s*\d*\s*\$?\s*([0-9,]+\.?\d*)', text, re.IGNORECASE)
        if min_payment_match:
            statement.minimum_payment = parse_amount(min_payment_match.group(1))
        
        # Extract account number - ALL formats
        # "Número de Cuenta: 4931-7300-3738-6081"
        account_match = re.search(r'Número\s+de\s+(?:Cuenta|Tarjeta):\s*([\d\-]+)', text, re.IGNORECASE)
        if account_match:
            # Get last 4 digits
            account_full = account_match.group(1).replace('-', '')
            statement.account_number = account_full[-4:] if len(account_full) >= 4 else account_full
        
        # Extract credit limit (if available)
        limit_match = re.search(r'Límite\s+de\s+crédito:\s*\$?\s*([0-9,]+\.\d{2})', text, re.IGNORECASE)
        if limit_match:
            statement.credit_limit = parse_amount(limit_match.group(1))
        
        # Extract available credit
        available_match = re.search(r'Crédito\s+disponible:\s*\$?\s*([0-9,]+\.\d{2})', text, re.IGNORECASE)
        if available_match:
            statement.available_credit = parse_amount(available_match.group(1))
    
    def _extract_transactions(self, text: str, statement: Statement):
        """Extract ALL transactions from Banorte statement."""
        transactions = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Banorte transaction format:
            # DD-MMM-YYYY DD-MMM-YYYY DESCRIPTION [INSTALLMENT_INFO] +/-$AMOUNT
            # Example: "23-NOV-2025 17-DIC-2025 BALANCE TRANSFER 16/24 +$2,186.99"
            
            trans_match = re.match(
                r'(\d{1,2}-[A-Z]{3}-\d{4})\s+(\d{1,2}-[A-Z]{3}-\d{4})\s+(.+?)\s+([\+\-])\s*\$\s*([0-9,]+\.\d{2})',
                line,
                re.IGNORECASE
            )
            
            if trans_match:
                transaction_date = trans_match.group(1)
                post_date = trans_match.group(2)
                description = trans_match.group(3).strip()
                sign = trans_match.group(4)
                amount_str = trans_match.group(5)
                
                # Skip if it looks like a header or total line
                if any(keyword in description.upper() for keyword in ['TOTAL', 'SALDO', 'SUBTOTAL']):
                    continue
                
                trans = Transaction()
                trans.statement_id = statement.id
                trans.date = parse_spanish_date(transaction_date)
                trans.post_date = parse_spanish_date(post_date)
                trans.description = description
                trans.description_normalized = normalize_description(description)
                
                amount = parse_amount(amount_str)
                # Apply sign (+ is charge, - is credit)
                trans.amount = amount if sign == '+' else -amount
                
                # Determine transaction type based on description
                desc_upper = description.upper()
                if any(keyword in desc_upper for keyword in ['PAGO', 'PAYMENT', 'ABONO']):
                    trans.transaction_type = 'payment'
                elif 'INTERESES' in desc_upper or 'INTEREST' in desc_upper:
                    trans.transaction_type = 'interest'
                    trans.has_interest = True
                elif 'COMISION' in desc_upper or 'FEE' in desc_upper or 'IVA' in desc_upper:
                    trans.transaction_type = 'fee'
                elif 'BALANCE TRANSFER' in desc_upper:
                    # Balance transfer payment (part of installment)
                    trans.transaction_type = 'expense'
                    trans.is_installment_payment = True
                else:
                    trans.transaction_type = 'expense'
                
                transactions.append(trans)
        
        return transactions
    
    def _extract_balance_transfers(self, text: str, statement: Statement):
        """Extract ALL balance transfer plans (Banorte's installment system)."""
        plans = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Banorte balance transfer format (very detailed):
            # DD-MMM-YYYY BALANCE TRANSFER $ORIGINAL $PENDING $INTEREST $TAX $PAYMENT XX/YY RATE%
            # Example: "29-MAY-2024 BALANCE TRANSFER $34,209.59 $8,235.27 $163.28 $23.13 $1,753.37 19/24 19.99%"
            
            bt_match = re.match(
                r'(\d{1,2}-[A-Z]{3}-\d{4})\s+BALANCE\s+TRANSFER(?:\s+DEBIT)?\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+(\d+)/(\d+)\s+([0-9.]+)%',
                line,
                re.IGNORECASE
            )
            
            if bt_match:
                plan = InstallmentPlan()
                plan.statement_id = statement.id
                plan.start_date = parse_spanish_date(bt_match.group(1))
                plan.description = 'BALANCE TRANSFER'
                if 'DEBIT' in line.upper():
                    plan.description += ' DEBIT'
                
                plan.original_amount = parse_amount(bt_match.group(2))
                plan.pending_balance = parse_amount(bt_match.group(3))
                plan.interest_this_period = parse_amount(bt_match.group(4))
                # group(5) is tax (IVA)
                plan.monthly_payment = parse_amount(bt_match.group(6))
                plan.current_installment = int(bt_match.group(7))
                plan.total_installments = int(bt_match.group(8))
                plan.interest_rate = Decimal(bt_match.group(9))
                
                plan.has_interest = True  # Balance transfers have interest
                plan.source_bank = self.bank_name
                plan.plan_type = 'balance_transfer'
                plan.status = 'active'
                
                # Calculate end date
                plan.calculate_end_date()
                
                plans.append(plan)
                continue
            
            # Also check for CONVENIENCE CHECK format
            check_match = re.match(
                r'(\d{1,2}-[A-Z]{3}-\d{4})\s+CONVENIENCE\s+CHECK(?:\s+DEBIT)?\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+\$\s*([0-9,]+\.\d{2})\s+(\d+)/(\d+)\s+([0-9.]+)%',
                line,
                re.IGNORECASE
            )
            
            if check_match:
                plan = InstallmentPlan()
                plan.statement_id = statement.id
                plan.start_date = parse_spanish_date(check_match.group(1))
                plan.description = 'CONVENIENCE CHECK'
                if 'DEBIT' in line.upper():
                    plan.description += ' DEBIT'
                
                plan.original_amount = parse_amount(check_match.group(2))
                plan.pending_balance = parse_amount(check_match.group(3))
                plan.interest_this_period = parse_amount(check_match.group(4))
                plan.monthly_payment = parse_amount(check_match.group(6))
                plan.current_installment = int(check_match.group(7))
                plan.total_installments = int(check_match.group(8))
                plan.interest_rate = Decimal(check_match.group(9))
                
                plan.has_interest = True
                plan.source_bank = self.bank_name
                plan.plan_type = 'convenience_check'
                plan.status = 'active'
                
                plan.calculate_end_date()
                
                plans.append(plan)
        
        return plans
