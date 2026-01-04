"""Liverpool bank statement extractor with OCR support."""

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

# OCR imports (optional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


class LiverpoolCreditExtractor(BaseExtractor):
    """Extractor for Liverpool credit card statements using OCR."""
    
    @property
    def bank_name(self) -> str:
        return "liverpool_credit"
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a Liverpool credit card statement."""
        try:
            # Try standard text extraction first
            with self._open_pdf(file_path) as pdf:
                for i in range(min(2, len(pdf.pages))):
                    text = self._extract_text_from_page(pdf.pages[i])
                    if 'LIVERPOOL' in text.upper() and 'CREDITO' in text.upper():
                        return True
            
            # If standard extraction fails, try OCR on first page
            if OCR_AVAILABLE:
                ocr_text = self._ocr_extract_text(file_path, pages=[0])
                if 'LIVERPOOL' in ocr_text.upper() or 'FABRICAS' in ocr_text.upper():
                    return True
            
            return False
        except Exception:
            return False
    
    def parse(self, file_path: str):
        """Parse Liverpool credit statement using OCR - Extract 100% of data."""
        if not OCR_AVAILABLE:
            raise ImportError(
                "OCR dependencies not installed. Run: "
                "pip install pytesseract pdf2image Pillow && "
                "sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils"
            )
        
        try:
            # Extract text using OCR
            full_text = self._ocr_extract_text(file_path)
            
            # Create statement
            statement = Statement()
            statement.bank = self.bank_name
            statement.source_type = "credit_card"
            statement.source_file = file_path
            
            # Extract summary
            self._extract_summary(full_text, statement)
            
            # Extract transactions
            transactions = self._extract_transactions(full_text, statement)
            
            # Extract MSI if available
            installment_plans = self._extract_msi(full_text, statement)
            
            # Store raw data
            statement.raw_data = json.dumps({
                'file_path': file_path,
                'extraction_date': datetime.now().isoformat(),
                'extraction_method': 'OCR'
            })
            
            return statement, transactions, installment_plans
            
        except Exception as e:
            print(f"Error parsing Liverpool credit statement: {e}")
            import traceback
            traceback.print_exc()
            return None, [], []
    
    def _ocr_extract_text(self, file_path: str, pages: list = None) -> str:
        """Extract text from PDF using OCR."""
        try:
            # Convert PDF to images
            if pages:
                images = convert_from_path(file_path, first_page=pages[0]+1, last_page=pages[-1]+1)
            else:
                images = convert_from_path(file_path)
            
            # Extract text from each image
            full_text = ""
            for i, image in enumerate(images):
                # Use Spanish language for better accuracy
                text = pytesseract.image_to_string(image, lang='spa+eng')
                full_text += f"\n--- PAGE {i+1} ---\n"
                full_text += text
            
            return full_text
        except Exception as e:
            print(f"OCR extraction error: {e}")
            return ""
    
    def _extract_summary(self, text: str, statement: Statement):
        """Extract summary from Liverpool statement."""
        
        # Period dates - Liverpool might use DD/MM/YYYY format
        period_patterns = [
            r'Periodo:?\s*(\d{2}/\d{2}/\d{4})\s*(?:al|a)\s*(\d{2}/\d{2}/\d{4})',
            r'Del\s+(\d{2}/\d{2}/\d{4})\s+al\s+(\d{2}/\d{2}/\d{4})',
        ]
        for pattern in period_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                # Convert DD/MM/YYYY to date
                try:
                    from datetime import datetime
                    statement.period_start = datetime.strptime(match.group(1), '%d/%m/%Y').date()
                    statement.period_end = datetime.strptime(match.group(2), '%d/%m/%Y').date()
                    break
                except:
                    pass
        
        # Payment amounts
        payment_patterns = [
            (r'[Pp]ago\s+(?:mínimo|minimo)[:\s]*\$?\s*([0-9,]+\.?\d*)', 'minimum_payment'),
            (r'[Pp]ago\s+(?:total|para\s+no\s+generar)[:\s]*\$?\s*([0-9,]+\.?\d*)', 'payment_no_interest'),
        ]
        for pattern, field in payment_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    amount = parse_amount(match.group(1))
                    setattr(statement, field, amount)
                except:
                    pass
        
        # Account number (last 4 digits)
        account_patterns = [
            r'[Tt]arjeta[:\s]*[\*\d\s]*(\d{4})',
            r'[Cc]uenta[:\s]*[\*\d\s]*(\d{4})',
        ]
        for pattern in account_patterns:
            match = re.search(pattern, text)
            if match:
                statement.account_number = match.group(1)
                break
    
    def _extract_transactions(self, text: str, statement: Statement):
        """Extract transactions from Liverpool statement."""
        transactions = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Liverpool transaction pattern (DD/MM/YYYY format assumed)
            # Pattern: DD/MM/YYYY DESCRIPTION $AMOUNT
            trans_match = re.match(
                r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$?\s*([0-9,]+\.?\d*)',
                line,
                re.IGNORECASE
            )
            
            if trans_match:
                date_str = trans_match.group(1)
                description = trans_match.group(2).strip()
                amount_str = trans_match.group(3)
                
                # Skip headers
                if any(kw in description.upper() for kw in ['FECHA', 'DESCRIPCION', 'TOTAL', 'SALDO']):
                    continue
                
                try:
                    trans = Transaction()
                    trans.statement_id = statement.id
                    trans.date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    trans.description = description
                    trans.description_normalized = normalize_description(description)
                    trans.amount = parse_amount(amount_str)
                    
                    # Determine type
                    desc_upper = description.upper()
                    if 'PAGO' in desc_upper:
                        trans.transaction_type = 'payment'
                        trans.amount = -trans.amount
                    elif 'INTERES' in desc_upper:
                        trans.transaction_type = 'interest'
                        trans.has_interest = True
                    elif 'COMISION' in desc_upper:
                        trans.transaction_type = 'fee'
                    else:
                        trans.transaction_type = 'expense'
                    
                    transactions.append(trans)
                except Exception as e:
                    # Skip malformed lines
                    continue
        
        return transactions
    
    def _extract_msi(self, text: str, statement: Statement):
        """Extract MSI plans if available."""
        plans = []
        
        lines = text.split('\n')
        
        for line in lines:
            # Liverpool MSI pattern: DESCRIPTION X de Y MESES $PAYMENT
            msi_match = re.match(
                r'(.+?)\s+(\d+)\s+de\s+(\d+)\s+(?:MESES|meses)\s+\$?\s*([0-9,]+\.?\d*)',
                line,
                re.IGNORECASE
            )
            
            if msi_match:
                try:
                    plan = InstallmentPlan()
                    plan.statement_id = statement.id
                    plan.description = msi_match.group(1).strip()
                    plan.current_installment = int(msi_match.group(2))
                    plan.total_installments = int(msi_match.group(3))
                    plan.monthly_payment = parse_amount(msi_match.group(4))
                    plan.has_interest = False  # Assume MSI unless stated
                    plan.source_bank = self.bank_name
                    plan.plan_type = 'msi'
                    plan.status = 'active'
                    
                    # Calculate remaining
                    plan.pending_balance = plan.monthly_payment * (plan.total_installments - plan.current_installment + 1)
                    
                    plan.calculate_end_date()
                    
                    plans.append(plan)
                except:
                    continue
        
        return plans


class LiverpoolDebitExtractor(BaseExtractor):
    """Extractor for Liverpool debit card statements using OCR."""
    
    @property
    def bank_name(self) -> str:
        return "liverpool_debit"
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a Liverpool debit card statement."""
        try:
            # Try OCR
            if OCR_AVAILABLE:
                from pdf2image import convert_from_path
                import pytesseract
                
                images = convert_from_path(file_path, first_page=1, last_page=1)
                if images:
                    text = pytesseract.image_to_string(images[0], lang='spa+eng')
                    return ('LIVERPOOL' in text.upper() and 
                            ('DEBITO' in text.upper() or 'CUENTA' in text.upper()))
            
            return False
        except Exception:
            return False
    
    def parse(self, file_path: str):
        """Parse Liverpool debit statement using OCR."""
        if not OCR_AVAILABLE:
            raise ImportError("OCR dependencies not installed")
        
        try:
            # Reuse credit extractor logic (debit is simpler, no MSI)
            credit_extractor = LiverpoolCreditExtractor()
            full_text = credit_extractor._ocr_extract_text(file_path)
            
            statement = Statement()
            statement.bank = self.bank_name
            statement.source_type = "debit_card"
            statement.source_file = file_path
            
            credit_extractor._extract_summary(full_text, statement)
            transactions = credit_extractor._extract_transactions(full_text, statement)
            
            # Debit cards don't have MSI
            installment_plans = []
            
            statement.raw_data = json.dumps({
                'file_path': file_path,
                'extraction_date': datetime.now().isoformat(),
                'extraction_method': 'OCR'
            })
            
            return statement, transactions, installment_plans
            
        except Exception as e:
            print(f"Error parsing Liverpool debit statement: {e}")
            import traceback
            traceback.print_exc()
            return None, [], []
