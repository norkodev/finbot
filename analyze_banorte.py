import pdfplumber
import re

print("="*60)
print("COMPREHENSIVE BANORTE PDF ANALYSIS")
print("="*60)

with pdfplumber.open('data/examples/BANORTE_TDC.pdf') as pdf:
    print(f'\nTotal pages: {len(pdf.pages)}')
    
    # Extract all text
    full_text = ''
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        full_text += text + '\n'
        if i < 3:  # Show first 3 pages
            print(f'\n{"="*60}')
            print(f'PAGE {i+1} (first 800 chars)')
            print("="*60)
            print(text[:800])
    
    print(f'\n{"="*60}')
    print('IDENTIFICATION MARKERS')
    print("="*60)
    
    # Bank identification
    markers = ['BANORTE', 'BANCO', 'TARJETA', 'ESTADO DE CUENTA']
    for marker in markers:
        if marker in full_text.upper():
            print(f'✓ Found: {marker}')
            # Show context
            idx = full_text.upper().find(marker)
            print(f'  Context: {full_text[max(0,idx-20):idx+50]}')
    
    print(f'\n{"="*60}')
    print('KEY SECTIONS DETECTION')
    print("="*60)
    
    # Period
    period_patterns = [
        r'Periodo:?\s*(\d{1,2}[-/][a-zA-Z]{3}[-/]\d{4})\s*(?:al|a)\s*(\d{1,2}[-/][a-zA-Z]{3}[-/]\d{4})',
        r'Del\s+(\d{1,2}[-/][a-zA-Z]{3}[-/]\d{4})\s+al\s+(\d{1,2}[-/][a-zA-Z]{3}[-/]\d{4})',
        r'(\d{1,2}[-/][a-zA-Z]{3}[-/]\d{4})\s*-\s*(\d{1,2}[-/][a-zA-Z]{3}[-/]\d{4})',
    ]
    for pattern in period_patterns:
        match = re.search(pattern, full_text, re.I)
        if match:
            print(f'✓ Period pattern: {pattern[:50]}...')
            print(f'  Found: {match.group(1)} to {match.group(2)}')
            break
    
    # Payment amounts
    payment_patterns = [
        r'[Pp]ago\s+(?:para\s+no\s+generar\s+)?(?:mínimo|intereses?)[:|\s]*\$?\s*([0-9,]+\.\d{2})',
        r'[Pp]ago\s+mínimo[:|\s]*\$?\s*([0-9,]+\.\d{2})',
        r'[Pp]ago\s+total[:|\s]*\$?\s*([0-9,]+\.\d{2})',
    ]
    for pattern in payment_patterns:
        matches = re.findall(pattern, full_text, re.I)
        if matches:
            print(f'✓ Payment pattern: {pattern[:40]}...')
            print(f'  Values: {matches[:3]}')
    
    print(f'\n{"="*60}')
    print('TRANSACTION PATTERNS')
    print("="*60)
    
    # Date patterns
    date_lines = []
    lines = full_text.split('\n')
    for i, line in enumerate(lines):
        if re.search(r'\d{1,2}[-/][a-zA-Z]{3}[-/]\d{4}', line, re.I):
            date_lines.append((i, line))
    
    print(f'✓ Lines with dates: {len(date_lines)}')
    print('\nFirst 10 date-containing lines:')
    for idx, line in date_lines[:10]:
        print(f'  Line {idx}: {line[:100]}')
    
    print(f'\n{"="*60}')
    print('MSI/INSTALLMENT DETECTION')
    print("="*60)
    
    # MSI patterns
    msi_keywords = ['MESES', 'MSI', 'DIFERIDO', 'CUOTA', 'DE ', 'PLAZO']
    for keyword in msi_keywords:
        count = full_text.upper().count(keyword)
        if count > 0:
            print(f'✓ "{keyword}" appears {count} times')
    
    # Look for "X de Y" pattern
    installment_pattern = r'(\d+)\s+de\s+(\d+)'
    matches = re.findall(installment_pattern, full_text, re.I)
    if matches:
        print(f'\n✓ Found "X de Y" patterns: {len(matches)} occurrences')
        print(f'  Examples: {matches[:5]}')
    
    print(f'\n{"="*60}')
    print('AMOUNT PATTERNS')
    print("="*60)
    
    # Find all amounts
    amount_pattern = r'\$\s*([0-9,]+\.\d{2})'
    amounts = re.findall(amount_pattern, full_text)
    print(f'✓ Total amounts found: {len(amounts)}')
    print(f'  Sample amounts: {amounts[:10]}')
    
    print(f'\n{"="*60}')
    print('SUMMARY')
    print("="*60)
    print(f'Total pages: {len(pdf.pages)}')
    print(f'Total characters: {len(full_text)}')
    print(f'Total lines: {len(lines)}')
    print(f'Lines with dates: {len(date_lines)}')
    print(f'Amounts found: {len(amounts)}')
