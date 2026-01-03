import pdfplumber
import re

with pdfplumber.open('data/examples/BANAMEX_CLASICA_TDC.pdf') as pdf:
    full_text = ''
    for page in pdf.pages:
        full_text += page.extract_text() + '\n'
    
    # Search for identifiers
    print('=== Identifying Markers ===')
    if 'BANAMEX' in full_text.upper():
        print('✓ Contains BANAMEX')
    if 'CLASICA' in full_text.upper():
        print('✓ Contains CLASICA')
    
    # Find key sections
    print('\n=== Key Sections Found ===')
    if 'Periodo:' in full_text:
        match = re.search(r'Periodo:\s*(\d{2}-[a-z]{3}-\d{4})\s+al\s+(\d{2}-[a-z]{3}-\d{4})', full_text, re.I)
        if match:
            print(f'✓ Periodo: {match.group(1)} al {match.group(2)}')
    
    if 'pago mínimo' in full_text.lower():
        match = re.search(r'pago mínimo:\s*\$?\s*([0-9,]+\.\d{2})', full_text, re.I)
        if match:
            print(f'✓ Pago mínimo: ${match.group(1)}')
    
    if 'pago para no generar intereses' in full_text.lower():
        match = re.search(r'pago para no generar intereses\s*\$?\s*([0-9,]+\.\d{2})', full_text, re.I)
        if match:
            print(f'✓ Pago sin intereses: ${match.group(1)}')
    
    # Look for transaction patterns
    print('\n=== Transaction Format Detection ===')
    lines = full_text.split('\n')
    trans_count = 0
    for line in lines:
        # Banamex format: DD-MMM-YYYY DESCRIPTION $AMOUNT
        if re.match(r'\d{2}-[a-z]{3}-\d{4}\s+.+\s+\$[0-9,]+\.\d{2}', line, re.I):
            if trans_count < 5:
                print(f'Sample: {line[:80]}')
            trans_count += 1
    print(f'\nTotal transaction-like lines found: {trans_count}')
    
    # Look for MSI section
    print('\n=== MSI Section Detection ===')
    if 'compras o cargos diferidos a meses' in full_text.lower():
        print('✓ Found MSI section')
    if 'compras a meses' in full_text.lower():
        print('✓ Found alternative MSI section')
