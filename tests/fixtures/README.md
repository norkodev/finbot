# Test Fixtures

This directory contains anonymized test PDFs for integration testing.

## Creating Test Fixtures

To create test fixtures from real PDFs:

1. **Take a real PDF statement**
2. **Anonymize sensitive data**:
   - Replace real names with "JOHN DOE"
   - Replace card numbers with "1234"
   - Change exact amounts slightly
   - Remove account numbers
3. **Save with naming convention**: `{bank}_sample.pdf`

## Expected Files

- `bbva_sample.pdf` - BBVA credit card statement
- `hsbc_sample.pdf` - HSBC credit card statement  
- `banamex_sample.pdf` - Banamex statement

## Privacy Note

**NEVER** commit real financial data to the repository.

All test fixtures must be anonymized before adding to git.
