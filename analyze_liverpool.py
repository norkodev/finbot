import pdfplumber
import re

print("ADVANCED LIVERPOOL PDF ANALYSIS")
print("="*70)

# Try different extraction methods
def try_extract(pdf_path, pages_to_check=3):
    with pdfplumber.open(pdf_path) as pdf:
        print(f'\nFile: {pdf_path}')
        print(f'Pages: {len(pdf.pages)}')
        
        for i in range(min(pages_to_check, len(pdf.pages))):
            page = pdf.pages[i]
            print(f'\n--- PAGE {i+1} ---')
            
            # Method 1: Standard extraction
            text1 = page.extract_text()
            if text1 and len(text1.strip()) > 100 and '�' not in text1[:500]:
                print(f'✓ Standard extraction works ({len(text1)} chars)')
                print(f'Sample: {text1[:200]}')
                return text1
            
            # Method 2: With layout preservation
            text2 = page.extract_text(layout=True)
            if text2 and len(text2.strip()) > 100 and '�' not in text2[:500]:
                print(f'✓ Layout extraction works ({len(text2)} chars)')
                print(f'Sample: {text2[:200]}')
                return text2
            
            # Method 3: Extract words
            words = page.extract_words()
            if words:
                text3 = ' '.join([w['text'] for w in words[:50]])
                print(f'✓ Word extraction: {len(words)} words')
                print(f'Sample: {text3[:200]}')
                if len(words) > 20:
                    return ' '.join([w['text'] for w in words])
            
            # Method 4: Extract tables
            tables = page.extract_tables()
            if tables:
                print(f'✓ Found {len(tables)} tables')
                for j, table in enumerate(tables[:2]):
                    print(f'  Table {j+1}: {len(table)} rows')
                    if table and len(table) > 0:
                        print(f'  First row: {table[0][:3]}')
        
        print('✗ No readable text found with any method')
        return None

# Analyze Liverpool TDC
print("\n" + "="*70)
print("LIVERPOOL TDC (Credit Card)")
print("="*70)
text_tdc = try_extract('data/examples/LIVER_TDC.pdf')

# Analyze Liverpool TDD
print("\n" + "="*70)
print("LIVERPOOL TDD (Debit Card)")
print("="*70)
text_tdd = try_extract('data/examples/LIVER_TDD.pdf')

# Summary
print("\n" + "="*70)
print("ANALYSIS SUMMARY")
print("="*70)
if text_tdc:
    print(f'✓ TDC: Readable ({len(text_tdc)} chars)')
else:
    print('✗ TDC: No readable text - may need OCR or special handling')

if text_tdd:
    print(f'✓ TDD: Readable ({len(text_tdd)} chars)')
else:
    print('✗ TDD: No readable text - may need OCR or special handling')
