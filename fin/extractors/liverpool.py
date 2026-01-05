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
import logging

# Setup logging
logger = logging.getLogger(__name__)

# OCR imports (optional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR dependencies not available. Install: pip install pytesseract pdf2image Pillow")


class LiverpoolCreditExtractor(BaseExtractor):
    """Extractor for Liverpool credit card statements using OCR."""
    
    @property
    def bank_name(self) -> str:
        return "liverpool_credit"
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file is a Liverpool credit card statement."""
        try:
            # First try filename - if it contains liverpool/credito, likely it's ours
            import os
            filename_lower = os.path.basename(file_path).lower()
            if 'liverpool' in filename_lower and any(kw in filename_lower for kw in ['credit', 'credito', 'tdc']):
                return True
            
            # Try standard text extraction
            with self._open_pdf(file_path) as pdf:
                for i in range(min(2, len(pdf.pages))):
                    text = self._extract_text_from_page(pdf.pages[i])
                    text_upper = text.upper()
                    if 'LIVERPOOL' in text_upper and any(kw in text_upper for kw in ['CREDITO', 'CRÉDITO', 'TARJETA']):
                        return True
            
            # If standard extraction fails, try OCR on first page
            if OCR_AVAILABLE:
                ocr_text = self._ocr_extract_text(file_path, pages=[0])
                ocr_upper = ocr_text.upper()
                # Be more lenient - look for Liverpool keywords
                liverpool_keywords = ['LIVERPOOL', 'FABRICAS', 'BOUTIQUE']
                credit_keywords = ['CREDITO', 'CRÉDITO', 'TARJETA', 'TDC']
                
                has_liverpool = any(kw in ocr_upper for kw in liverpool_keywords)
                has_credit = any(kw in ocr_upper for kw in credit_keywords)
                
                if has_liverpool or has_credit:
                    return True
            
            return False
        except Exception as e:
            # Don't silently fail - log the error
            print(f"can_parse error for {file_path}: {e}")
            return False
    
    def parse(self, file_path: str):
        """Parse Liverpool credit statement using OCR - Extract 100% of data."""
        if not OCR_AVAILABLE:
            raise ImportError(
                "OCR dependencies not installed. Run: "
                "pip install pytesseract pdf2image Pillow && "
                "sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils"
            )
        
        logger.info(f"Starting Liverpool Credit extraction for: {file_path}")
        
        # Initialize with defaults for partial results
        statement = Statement()
        statement.bank = self.bank_name
        statement.source_type = "credit_card"
        statement.source_file = file_path
        transactions = []
        installment_plans = []
        
        try:
            # Extract text using OCR
            logger.info("Step 1/4: Extracting text with OCR...")
            full_text = self._ocr_extract_text(file_path)
            
            if not full_text or len(full_text.strip()) < 50:
                logger.error("OCR extraction failed or returned very little text")
                return None, [], []
            
            logger.info(f"OCR extracted {len(full_text)} characters")
            
            # Extract summary
            logger.info("Step 2/4: Extracting summary...")
            try:
                self._extract_summary(full_text, statement)
                logger.info(f"Summary extracted: period {statement.period_start} to {statement.period_end}")
            except Exception as e:
                logger.warning(f"Summary extraction failed: {e}")
                # Continue anyway - we can still extract transactions
            
            # Extract transactions
            logger.info("Step 3/4: Extracting transactions...")
            try:
                transactions = self._extract_transactions(full_text, statement)
                logger.info(f"Extracted {len(transactions)} transactions")
            except Exception as e:
                logger.error(f"Transaction extraction failed: {e}")
                # Continue - partial results are better than nothing
            
            # Extract MSI if available
            logger.info("Step 4/4: Extracting MSI plans...")
            try:
                installment_plans = self._extract_msi(full_text, statement)
                logger.info(f"Extracted {len(installment_plans)} MSI plans")
            except Exception as e:
                logger.warning(f"MSI extraction failed: {e}")
                # MSI is optional, continue
            
            # Store raw data
            statement.raw_data = json.dumps({
                'file_path': file_path,
                'extraction_date': datetime.now().isoformat(),
                'extraction_method': 'OCR',
                'text_length': len(full_text)
            })
            
            # Return partial results if we got at least some transactions
            if len(transactions) > 0:
                logger.info(f"✓ Liverpool Credit extraction successful: {len(transactions)} transactions")
                return statement, transactions, installment_plans
            else:
                logger.warning("No transactions extracted - returning None")
                return None, [], []
            
        except Exception as e:
            logger.error(f"Critical error parsing Liverpool credit statement: {e}")
            import traceback
            traceback.print_exc()
            
            # Return partial results if we have any
            if len(transactions) > 0:
                logger.info(f"Returning partial results: {len(transactions)} transactions despite error")
                return statement, transactions, installment_plans
            
            return None, [], []
    
    def _ocr_extract_text(self, file_path: str, pages: list = None) -> str:
        """Extract text from PDF using OCR."""
        try:
            logger.debug(f"Converting PDF to images: {file_path}")
            
            # Convert PDF to images
            if pages:
                images = convert_from_path(file_path, first_page=pages[0]+1, last_page=pages[-1]+1, dpi=300)
            else:
                images = convert_from_path(file_path, dpi=300)
            
            if not images:
                logger.error("PDF to image conversion returned no images")
                return ""
            
            logger.debug(f"Converted to {len(images)} images")
            
            # Extract text from each image
            full_text = ""
            for i, image in enumerate(images):
                try:
                    # Use Spanish language for better accuracy
                    logger.debug(f"Processing page {i+1}/{len(images)}")
                    text = pytesseract.image_to_string(image, lang='spa+eng', config='--psm 6')
                    full_text += f"\n--- PAGE {i+1} ---\n"
                    full_text += text
                    logger.debug(f"Page {i+1}: extracted {len(text)} characters")
                except Exception as page_error:
                    logger.error(f"Error processing page {i+1}: {page_error}")
                    continue
            
            return full_text
            
        except Exception as e:
            logger.error(f"OCR extraction error: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _extract_summary(self, text: str, statement: Statement):
        """Extract summary from Liverpool statement."""
        
        # Period dates - Liverpool might use DD/MM/YYYY format
        # Period dates - Liverpool might use DD/MM/YYYY or DD-MMM-YYYY
        
        month_map = {
            'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
        }

        period_patterns = [
            r'Periodo:?\s*(\d{2}/\d{2}/\d{4})\s*(?:al|a)\s*(\d{2}/\d{2}/\d{4})',
            r'Del\s+(\d{2}/\d{2}/\d{4})\s+al\s+(\d{2}/\d{2}/\d{4})',
            r'FECHA DE CORTE\s+(\d{2})-([A-Z]{3})-(\d{4})'
        ]
        for pattern in period_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    if len(match.groups()) == 3 and '-' in match.group(0): # Spanish date format
                         day = int(match.group(1))
                         month_str = match.group(2).upper()
                         year = int(match.group(3))
                         if month_str in month_map:
                             statement.period_end = datetime(year, month_map[month_str], day).date()
                             # Infer start date (approx 30 days before)
                             from datetime import timedelta
                             statement.period_start = statement.period_end - timedelta(days=30)
                             break
                    else:
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
        
        # Month mapping
        month_map = {
            'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
        }
        
        # Determine statement year from period_end or current year
        stmt_year = statement.period_end.year if statement.period_end else datetime.now().year
        stmt_month = statement.period_end.month if statement.period_end else datetime.now().month
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Liverpool transaction patterns
            # 1. DD/MM/YYYY
            # 2. DD-MMM (e.g. 12-DIC, 23.NOV, 27NOV)
            
            # Pattern 1: Standard date
            match_std = re.match(r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$?\s*([0-9,]+\.?\d*)', line, re.IGNORECASE)
            
            # Pattern 2: OCR Spanish date (flexible separator)
            # Matches: 12-DIC, 12.DIC, 12 DIC, 12DIC
            # Also handles OCR errors like 'ol-DIC' -> '01-DIC' if needed (advanced)
            match_ocr = re.match(r'(\d{2})[.\-\s]?([A-Z]{3})\s+(.+?)\s+\$?\s*([0-9,]+\.?\d*)', line, re.IGNORECASE)
            
            date_obj = None
            description = ""
            amount_str = ""
            
            if match_std:
                try:
                    date_obj = datetime.strptime(match_std.group(1), '%d/%m/%Y').date()
                    description = match_std.group(2).strip()
                    amount_str = match_std.group(3)
                except: pass
            elif match_ocr:
                try:
                    day = int(match_ocr.group(1))
                    month_str = match_ocr.group(2).upper()
                    description = match_ocr.group(3).strip()
                    amount_str = match_ocr.group(4)
                    
                    if month_str in month_map:
                        month = month_map[month_str]
                        # Logic to determine year:
                        # If transaction month is Dec and statement is Jan, it's prev year
                        # If trans month > stmt month + 1, likely prev year (e.g. stmt Jan, trans Nov)
                        trans_year = stmt_year
                        if month > stmt_month + 1: 
                            trans_year -= 1
                        elif month == 12 and stmt_month == 1:
                            trans_year -= 1
                            
                        date_obj = datetime(trans_year, month, day).date()
                except: pass
            
            if date_obj and description and amount_str:
                # Cleanup description - remove trailing codes
                # often OCR adds noise like "PRESUPUESTO 37363 20.00 USD"
                # We keep it for now but cleaner description is better
                
                # Skip headers
                if any(kw in description.upper() for kw in ['FECHA', 'DESCRIPCION', 'TOTAL', 'SALDO', 'SEGMENTO']):
                    continue
                
                try:
                    trans = Transaction()
                    trans.statement_id = statement.id
                    trans.date = date_obj
                    trans.description = description
                    trans.description_normalized = normalize_description(description)
                    try:
                        trans.amount = parse_amount(amount_str)
                    except: continue # Skip if amount invalid
                    
                    # Determine type
                    desc_upper = description.upper()
                    if 'PAGO' in desc_upper:
                        trans.transaction_type = 'payment'
                        trans.amount = -abs(trans.amount) # Ensure payment is negative
                    elif any(kw in desc_upper for kw in ['INTERES', 'COMISION', 'CUOTA']):
                        trans.transaction_type = 'fee' # Simplified
                        if 'INTERES' in desc_upper:
                             trans.has_interest = True
                             trans.transaction_type = 'interest'
                    else:
                        trans.transaction_type = 'expense'
                    
                    transactions.append(trans)
                except Exception:
                    continue
        
        return transactions
    
    def _extract_msi(self, text: str, statement: Statement):
        """Extract MSI plans if available.
        
        Liverpool MSI format (from OCR of table on pages 2-3):
        DATE CODE INSTALLMENT# MENS TYPE PROMO LPC TOTAL# AMOUNTS...
        Example: @ENE 037 18 MENS SANT PROMOC LPC 12 24,800.44 0.00 3,100.15 21,699.45
        """
        plans = []
        
        lines = text.split('\n')
        
        for line in lines:
            # Liverpool MSI pattern from table:
            # Format: NN MENS [SANT|SINT] PROMOC LPC TOTAL SALDO_ANT CARGOS MENSUALIDAD SALDO_FINAL
            #  Where NN = current installment paid, TOTAL = total installments
            msi_match = re.search(
                r'(\d{1,2})\s+MENS\s+\w+\s+\w+\s+\w+\s+(\d+)\s+[\d,]+\.\d+\s+[\d,\.]+\s+([\d,]+\.\d+)',
                line,
                re.IGNORECASE
            )
            
            if msi_match:
                try:
                    plan = InstallmentPlan()
                    plan.statement_id = statement.id
                    
                    # Extract from table columns
                    current_inst = int(msi_match.group(1))
                    total_inst = int(msi_match.group(2))
                    monthly_payment = parse_amount(msi_match.group(3))
                    
                    # Get description from the line (extract DATE and plan code)
                    desc_match = re.search(r'([\d@-]+[A-Z]{3}|[\d-]+[A-Z]{3})\s+(\d{3})', line)
                    if desc_match:
                        plan.description = f"Plan {desc_match.group(2)} - {desc_match.group(1)}"
                    else:
                        plan.description = "Plan Liverpool MSI"
                    
                    plan.current_installment = current_inst
                    plan.total_installments = total_inst
                    plan.monthly_payment = monthly_payment
                    
                    # Calculate original amount (monthly payment * total installments)
                    plan.original_amount = monthly_payment * total_inst
                    
                    # Determine if it has interest based on keyword
                    # SANT = Con interés, SINT = Sin interés
                    has_interest = 'SANT' in line.upper()
                    plan.has_interest = has_interest
                    
                    plan.source_bank = self.bank_name
                    plan.plan_type = 'msi' if not has_interest else 'installment'
                    plan.status = 'active'
                    
                    # Calculate remaining
                    remaining_payments = total_inst - current_inst
                    if remaining_payments < 0:
                        remaining_payments = 0
                    plan.pending_balance = monthly_payment * remaining_payments
                    
                    plan.calculate_end_date()
                    
                    plans.append(plan)
                    logger.debug(f"Extracted MSI: {plan.description} - {current_inst}/{total_inst} @ ${monthly_payment}")
                    
                except Exception as e:
                    logger.warning(f"Failed to parse MSI line: {line[:100]} - {e}")
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
        
        logger.info(f"Starting Liverpool Debit extraction for: {file_path}")
        
        # Initialize with defaults
        statement = Statement()
        statement.bank = self.bank_name
        statement.source_type = "debit_card"
        statement.source_file = file_path
        transactions = []
        
        try:
            # Reuse credit extractor logic (debit is simpler, no MSI)
            credit_extractor = LiverpoolCreditExtractor()
            
            logger.info("Step 1/3: Extracting text with OCR...")
            full_text = credit_extractor._ocr_extract_text(file_path)
            
            if not full_text or len(full_text.strip()) < 50:
                logger.error("OCR extraction failed or returned very little text")
                return None, [], []
            
            logger.info(f"OCR extracted {len(full_text)} characters")
            
            logger.info("Step 2/3: Extracting summary...")
            try:
                credit_extractor._extract_summary(full_text, statement)
            except Exception as e:
                logger.warning(f"Summary extraction failed: {e}")
            
            logger.info("Step 3/3: Extracting transactions...")
            try:
                transactions = credit_extractor._extract_transactions(full_text, statement)
                logger.info(f"Extracted {len(transactions)} transactions")
            except Exception as e:
                logger.error(f"Transaction extraction failed: {e}")
            
            # Debit cards don't have MSI
            installment_plans = []
            
            statement.raw_data = json.dumps({
                'file_path': file_path,
                'extraction_date': datetime.now().isoformat(),
                'extraction_method': 'OCR',
                'text_length': len(full_text)
            })
            
            # Return partial results if we got at least some transactions
            if len(transactions) > 0:
                logger.info(f"✓ Liverpool Debit extraction successful: {len(transactions)} transactions")
                return statement, transactions, installment_plans
            else:
                logger.warning("No transactions extracted - returning None")
                return None, [], []
            
        except Exception as e:
            logger.error(f"Critical error parsing Liverpool debit statement: {e}")
            import traceback
            traceback.print_exc()
            
            # Return partial results if we have any
            if len(transactions) > 0:
                logger.info(f"Returning partial results: {len(transactions)} transactions despite error")
                return statement, transactions, installment_plans
            
            return None, [], []
