"""HSBC bank statement extractor."""

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


class HSBCExtractor(BaseExtractor):
    """Extractor for HSBC bank statements."""
    
    @property
    def bank_name(self) -> str:
        return "hsbc"
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is an HSBC statement."""
        try:
            with self._open_pdf(file_path) as pdf:
                # HSBC identifier appears on page 2, so check first 2 pages
                for i in range(min(2, len(pdf.pages))):
                    text = self._extract_text_from_page(pdf.pages[i])
                    if 'HSBC AIR' in text.upper() or 'HSBC MEXICO' in text.upper():
                        return True
                return False
        except Exception:
            return False
    
    def parse(self, file_path: str):
        """Parse HSBC statement."""
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
                
                # Extract transactions
                transactions = []
                transactions.extend(self._extract_regular_transactions(full_text, statement))
                
                # Extract balance transfers (HSBC's version of MSI)
                installment_plans = []
                installment_plans.extend(self._extract_balance_transfers(full_text, statement))
                
                # Store raw data
                statement.raw_data = json.dumps({
                    'file_path': file_path,
                    'extraction_date': datetime.now().isoformat()
                })
                
                return statement, transactions, installment_plans
                
        except Exception as e:
            print(f"Error parsing HSBC statement: {e}")
            import traceback
            traceback.print_exc()
            return None, [], []
    
    def _extract_summary(self, text: str, statement: Statement):
        """Extract summary information from HSBC statement."""
        
        # Extract period dates  
        # Format: "Periodo: 20-Nov-2025 al 19-Dic-2025"
        period_match = re.search(r'Periodo:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})\s+al\s+(\d{1,2}-[A-Za-z]{3}-\d{4})', text, re.IGNORECASE)
        if period_match:
            statement.period_start = parse_spanish_date(period_match.group(1))
            statement.period_end = parse_spanish_date(period_match.group(2))
        
        # Extract statement date (fecha de corte)
        corte_match = re.search(r'Fecha\s+de\s+corte:\s*(\d{1,2}-[A-Za-z]{3}-\d{4})', text, re.IGNORECASE)
        if corte_match:
            statement.statement_date = parse_spanish_date(corte_match.group(1))
        
        # Extract due date - HSBC format may include day of week: "d) Fecha límite de pago: 1 sábado, 10-Ene-2026"
        due_match = re.search(r'Fecha\s+l[íi]mite\s+de\s+pago:.*?(?:\d+\s+)?(?:\w+,\s+)?(\d{1,2}-[A-Za-z]{3}-\d{4})', text, re.IGNORECASE)
        if due_match:
            statement.due_date = parse_spanish_date(due_match.group(1))
        
        # Extract payments
        # "PAGO PARA NO GENERAR INTERESES: $ XX,XXX.XX"
        no_interest_match = re.search(r'PAGO\s+PARA\s+NO\s+GENERAR\s+INTERESES:\s*\$?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if no_interest_match:
            statement.payment_no_interest = parse_amount(no_interest_match.group(1))
        
        # "Pago mínimo" - HSBC format: "g) Pago mínimo : 4 $ 2,721.44"
        # May have letter prefix, extra spaces, and number before amount
        min_payment_match = re.search(r'[a-z]\)\s+Pago\s+m[íi]nimo\s*:\s*\d*\s*\$?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if not min_payment_match:
            # Fallback to simpler pattern
            min_payment_match = re.search(r'Pago\s+m[íi]nimo\s*:\s*\d*\s*\$?\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if min_payment_match:
            statement.minimum_payment = parse_amount(min_payment_match.group(1))
        
        # Extract account number (last 4 digits)
        account_match = re.search(r'NÚMERO\s+DE\s+CUENTA:\s*\d+\s+\d+\s+\d+\s+(\d{4})', text, re.IGNORECASE)
        if not account_match:
            account_match = re.search(r'Número\s+de\s+cuenta:\s*\d+\s+\d+\s+\d+\s+(\d{4})', text, re.IGNORECASE)
        if account_match:
            statement.account_number = account_match.group(1)
    
    def _extract_regular_transactions(self, text: str, statement: Statement):
        """Extract regular transactions from HSBC statement."""
        transactions = []
        
        # Find the regular transactions section
        # "CARGOS, ABONOS Y COMPRAS REGULARES (NO A MESES)"
        section_match = re.search(
            r'CARGOS,\s*ABONOS\s*Y\s*COMPRAS\s*REGULARES\s*\(NO\s*A\s*MESES\s*\).*?Tarjeta\s+titular.*?\n(.*?)(?=ATENCIÓN DE QU|Información SPEI|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        
        if not section_match:
            return transactions
        
        section_text = section_match.group(1)
        lines = section_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match transaction pattern
            # Format: DD-MMM-YYYY DD-MMM-YYYY DESCRIPTION +/- $AMOUNT
            trans_match = re.match(
                r'(\d{1,2}-[A-Za-z]{3}-\d{4})\s+(\d{1,2}-[A-Za-z]{3}-\d{4})\s+(.+?)\s+([+\-])\s*\$\s*([\d,]+\.\d{2})',
                line,
                re.IGNORECASE
            )
            
            if trans_match:
                date_str = trans_match.group(1)
                post_date_str = trans_match.group(2)
                description = trans_match.group(3).strip()
                sign = trans_match.group(4)
                amount_str = trans_match.group(5)
                
                # Create transaction
                trans = Transaction()
                trans.statement_id = statement.id
                trans.date = parse_spanish_date(date_str)
                trans.post_date = parse_spanish_date(post_date_str)
                trans.description = description
                trans.description_normalized = normalize_description(description)
                
                amount = parse_amount(amount_str)
                trans.amount = -amount if sign == '-' else amount
                
                # Determine transaction type
                desc_upper = description.upper()
                if 'PAGO' in desc_upper or 'SPEI' in desc_upper:
                    trans.transaction_type = 'payment'
                elif 'INTERESES' in desc_upper:
                    trans.transaction_type = 'interest'
                    trans.has_interest = True
                elif 'PENALIZACION' in desc_upper or 'COMISION' in desc_upper:
                    trans.transaction_type = 'fee'
                else:
                    trans.transaction_type = 'expense'
                
                transactions.append(trans)
        
        return transactions
    
    def _extract_balance_transfers(self, text: str, statement: Statement):
        """Extract balance transfers (HSBC's version of MSI)."""
        plans = []
        
        # Find balance transfer section
        # "COMPRAS Y CARGOS DIFERIDOS A MESES CON INTERESES"
        section_match = re.search(
            r'COMPRAS\s+Y\s+CARGOS\s+DIFERIDOS\s+A\s+MESES\s+CON\s+INTERESES.*?Tarjeta\s+titular.*?aplicable\n(.*?)(?=CARGOS,\s*ABONOS\s*Y\s*COMPRAS\s*REGULARES|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        
        if not section_match:
            return plans
        
        section_text = section_match.group(1)
        lines = section_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match balance transfer line
            # Format: DD-MMM-YYYY DESCRIPTION $ORIGINAL $PENDING $INTEREST $IVA $PAYMENT NN de MM RATE%
            transfer_match = re.match(
                r'(\d{1,2}-[A-Za-z]{3}-\d{4})\s+(.+?)\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+(\d+)\s+de\s+(\d+)\s+([\d.]+)%',
                line,
                re.IGNORECASE
            )
            
            if transfer_match:
                plan = InstallmentPlan()
                plan.statement_id = statement.id
                plan.start_date = parse_spanish_date(transfer_match.group(1))
                plan.description = transfer_match.group(2).strip()
                plan.original_amount = parse_amount(transfer_match.group(3))
                plan.pending_balance = parse_amount(transfer_match.group(4))
                plan.interest_this_period = parse_amount(transfer_match.group(5))
                # group(6) is IVA, group(7) is payment
                plan.monthly_payment = parse_amount(transfer_match.group(7))
                plan.current_installment = int(transfer_match.group(8))
                plan.total_installments = int(transfer_match.group(9))
                plan.interest_rate = Decimal(transfer_match.group(10))
                plan.has_interest = True
                plan.source_bank = self.bank_name
                plan.plan_type = 'balance_transfer'
                plan.status = 'active'
                
                # Calculate end date
                plan.calculate_end_date()
                
                plans.append(plan)
        
        return plans
