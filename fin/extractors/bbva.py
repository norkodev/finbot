"""Improved BBVA bank statement extractor based on real PDF format."""

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
                
                # Extract transactions
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
            import traceback
            traceback.print_exc()
            return None, [], []
    
    def _extract_summary(self, text: str, statement: Statement):
        """Extract summary information from statement."""
        
        # Extract period dates
        period_match = re.search(r'Periodo:\s*(\d{2}-[a-z]{3}-\d{4})\s*al\s*(\d{2}-[a-z]{3}-\d{4})', text, re.IGNORECASE)
        if period_match:
            statement.period_start = parse_spanish_date(period_match.group(1))
            statement.period_end = parse_spanish_date(period_match.group(2))
        
        # Extract statement date (fecha de corte)
        corte_match = re.search(r'Fecha\s+de\s+corte:\s*(\d{2}-[a-z]{3}-\d{4})', text, re.IGNORECASE)
        if corte_match:
            statement.statement_date = parse_spanish_date(corte_match.group(1))
        
        # Extract due date (fecha límite de pago)
        due_match = re.search(r'Fecha\s+límite\s+de\s+pago:.*?(\d{2}-[a-z]{3}-\d{4})', text, re.IGNORECASE)
        if due_match:
            statement.due_date = parse_spanish_date(due_match.group(1))
        
        # Extract payment amounts
        # Pago para no generar intereses
        no_interest_match = re.search(r'Pago\s+para\s+no\s+generar\s+intereses.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if no_interest_match:
            statement.payment_no_interest = parse_amount(no_interest_match.group(1))
        
        # Pago mínimo
        min_payment_match = re.search(r'Pago\s+mínimo:.*?\$\s*([\d,]+\.\d{2})', text, re.IGNORECASE)
        if min_payment_match:
            statement.minimum_payment = parse_amount(min_payment_match.group(1))
        
        # Extract account number (last 4 digits)
        account_match = re.search(r'Número\s+de\s+tarjeta:\s*\d+(\d{4})', text, re.IGNORECASE)
        if account_match:
            statement.account_number = account_match.group(1)
    
    def _extract_regular_transactions(self, text: str, statement: Statement):
        """Extract regular transactions from statement."""
        transactions = []
        
        # Find the regular transactions section
        section_match = re.search(
            r'CARGOS,COMPRAS Y ABONOS REGULARES\(NO A MESES\).*?Tarjeta titular.*?\n(.*?)(?=COMPRAS Y CARGOS DIFERIDOS A MESES|Notas:|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        
        if not section_match:
            return transactions
        
        section_text = section_match.group(1)
        
        # Parse transaction lines
        # Format: DD-MMM-YYYY DD-MMM-YYYY DESCRIPTION +/-  $AMOUNT
        lines = section_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match transaction pattern
            # Example: "15-nov-2025 18-nov-2025 CANTIA SA DE CV + $811.55"
            trans_match = re.match(
                r'(\d{2}-[a-z]{3}-\d{4})\s+(\d{2}-[a-z]{3}-\d{4})\s+(.+?)\s+([+\-])\s*\$\s*([\d,]+\.\d{2})',
                line,
                re.IGNORECASE
            )
            
            if trans_match:
                date_str = trans_match.group(1)
                post_date_str = trans_match.group(2)
                description = trans_match.group(3).strip()
                sign = trans_match.group(4)
                amount_str = trans_match.group(5)
                
                # Skip lines that are details (IVA, Interes, etc.)
                if any(keyword in description.upper() for keyword in ['IVA :', 'INTERES:', 'COMISIONES:', 'CAPITAL:', 'PAGO EXCEDENTE:']):
                    continue
                
                # Create transaction
                trans = Transaction()
                trans.statement_id = statement.id
                trans.date = parse_spanish_date(date_str)
                trans.post_date = parse_spanish_date(post_date_str)
                trans.description = description
                trans.description_normalized = normalize_description(description)
                
                amount = parse_amount(amount_str)
                # Apply sign
                trans.amount = -amount if sign == '-' else amount
                
                # Determine transaction type
                desc_upper = description.upper()
                if 'PAGO' in desc_upper:
                    trans.transaction_type = 'payment'
                elif 'INTERES' in desc_upper:
                    trans.transaction_type = 'interest'
                    trans.has_interest = True
                elif 'COMISION' in desc_upper or 'ANUALIDAD' in desc_upper:
                    trans.transaction_type = 'fee'
                else:
                    trans.transaction_type = 'expense'
                
                # Check if it's an installment payment (has XX DE YY pattern)
                installment_info = extract_installment_info(description)
                if installment_info:
                    trans.is_installment_payment = True
                
                transactions.append(trans)
        
        return transactions
    
    def _extract_msi_no_interest(self, text: str, statement: Statement):
        """Extract MSI without interest plans."""
        plans = []
        
        # Find MSI section
        section_match = re.search(
            r'COMPRAS Y CARGOS DIFERIDOS A MESES SIN INTERESES.*?Tarjeta titular.*?aplicable\n(.*?)(?=COMPRAS Y CARGOS DIFERIDOS A MESES CON INTERESES|CARGOS,COMPRAS Y ABONOS REGULARES|$)',
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
            
            # Match MSI line
            # Format: DD-MMM-YYYY DESCRIPTION $AMOUNT $PENDING $PAYMENT NN de MM 0.00%
            msi_match = re.match(
                r'(\d{2}-[a-z]{3}-\d{4})\s+(.+?)\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+(\d+)\s+de\s+(\d+)\s+(\d+\.\d{2})%',
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
                plan.interest_rate = Decimal(msi_match.group(8))
                plan.has_interest = False
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
        section_match = re.search(
            r'COMPRAS Y CARGOS DIFERIDOS A MESES CON INTERESES.*?Tarjeta titular.*?aplicable\n(.*?)(?=CARGOS,COMPRAS Y ABONOS REGULARES|$)',
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
            
            # Match MSI with interest line
            # Format: DD-MMM-YYYY DESCRIPTION $ORIGINAL $PENDING $INTEREST $IVA $PAYMENT NN de MM RATE% TERM
            msi_match = re.match(
                r'(\d{2}-[a-z]{3}-\d{4})\s+(.+?)\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+\$\s*([\d,]+\.\d{2})\s+(\d+)\s+de\s+(\d+)\s+(\d+\.\d{2})%',
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
                plan.interest_this_period = parse_amount(msi_match.group(5))
                plan.monthly_payment = parse_amount(msi_match.group(7))
                plan.current_installment = int(msi_match.group(8))
                plan.total_installments = int(msi_match.group(9))
                plan.interest_rate = Decimal(msi_match.group(10))
                plan.has_interest = True
                plan.source_bank = self.bank_name
                plan.plan_type = 'efectivo_inmediato' if 'EFECTIVO INMEDIATO' in plan.description.upper() else 'msi_with_interest'
                plan.status = 'active'
                
                # Calculate end date
                plan.calculate_end_date()
                
                plans.append(plan)
        
        return plans
