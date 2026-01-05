# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Finbot is a local-first financial intelligence system for personal finance management. It processes PDF bank statements from Mexican banks, extracts and classifies transactions using AI, and provides financial insights through RAG-powered chat.

**Key Characteristics:**
- 100% local: No cloud dependencies, all data stays on the user's machine
- AI-powered: Uses local LLM (Ollama + Qwen2.5) for classification and RAG chat
- Multi-bank: Supports 7 Mexican banks with custom PDF parsers
- Production-ready: Active monthly workflow processing real financial data

## Common Commands

### Development & Testing
```bash
# Run all tests with coverage
pytest tests/ -v --cov=fin

# Run specific test file
pytest tests/test_extractors/test_bbva.py -v

# Run tests for specific module
pytest tests/test_classification/ -v

# Install package in editable mode (after environment changes)
pip install -e .
```

### Processing Workflow
```bash
# Process bank statements (with LLM classification)
fin process data/inbox/2025/12/

# Process without LLM (faster, rules only)
fin process data/inbox/2025/12/ --skip-llm

# Force reprocess already-processed files
fin process data/inbox/2025/12/ --force

# Interactive classification correction (teaches the system)
fin correct --limit 10

# Generate all reports for a month
fin reports --month 2025-12

# Rebuild vector index for RAG
fin index --rebuild

# Index specific month
fin index --month 2025-12

# Start AI chat assistant
fin chat
```

### Database Access
```bash
# The database is SQLite at: data/finbot.db
sqlite3 data/finbot.db

# Useful queries:
# - Count transactions: SELECT COUNT(*) FROM transactions;
# - Recent transactions: SELECT date, description, amount FROM transactions ORDER BY date DESC LIMIT 10;
# - Unclassified: SELECT COUNT(*) FROM transactions WHERE category IS NULL;
```

### Production Workflow
```bash
# End-to-end validation (recommended before production use)
./validate_e2e.sh

# Typical monthly routine:
# 1. Place PDFs in data/inbox/YYYY/MM/
# 2. fin process data/inbox/YYYY/MM/
# 3. fin correct --limit 20  (review/fix classifications)
# 4. fin reports --month YYYY-MM
# 5. fin index --month YYYY-MM
```

## Architecture Overview

### 3-Tier Classification System
The system classifies transactions in priority order:
1. **Merchant History** (highest priority): If a merchant was previously classified (manually via `fin correct` or LLM), reuse that category
2. **Rule Engine**: Regex-based pattern matching from `fin/config/rules.yaml`
3. **LLM Fallback** (lowest priority): Batch classification via Ollama (only if previous tiers fail)

Location: `fin/classification/classifier.py:55-100`

**Critical**: The classification order ensures user corrections (via `fin correct`) always take precedence.

### Bank Statement Extractors
Each bank has a dedicated parser inheriting from `BaseExtractor`:
- Location: `fin/extractors/`
- Pattern: `{bank_name}.py` (e.g., `bbva.py`, `hsbc.py`)
- Detection: `BankDetector` auto-identifies bank from PDF content
- Supported: BBVA, HSBC, Banamex, Banorte, Liverpool (credit/debit with OCR)

**Adding a new bank:**
1. Create `fin/extractors/newbank.py` extending `BaseExtractor`
2. Implement `can_parse()` (bank detection logic) and `parse()` (extraction)
3. Register in `fin/extractors/__init__.py`
4. Add test PDF to `tests/fixtures/` and test file

### RAG Chat System
Multi-component RAG pipeline for financial Q&A:
- **Document Generation**: Monthly summaries, commitments, merchant profiles (`fin/reports/`)
- **Vectorization**: ChromaDB + sentence-transformers embeddings (`fin/vectorization/`)
- **Retrieval**: Hybrid search with metadata filtering (`fin/rag/retrieval.py`)
- **Generation**: Ollama LLM with financial context + guardrails (`fin/rag/chat_engine.py`)

**Document flow:**
1. `fin reports` → generates markdown documents
2. `fin index` → chunks documents → embeddings → ChromaDB
3. `fin chat` → user question → retrieve relevant docs → LLM generation

Location: `fin/rag/chat_engine.py:45-150`

### Data Models (SQLAlchemy)
Core tables in SQLite (`fin/models/`):
- `statements`: Bank statement metadata (one per PDF)
- `transactions`: Individual transactions (linked to statement)
- `installment_plans`: MSI (meses sin intereses) installment tracking
- `merchants`: Merchant catalog with learned classifications
- `processing_log`: File processing history (prevents reprocessing)

**Key relationships:**
- Statement 1→N Transactions
- Transaction N→1 Merchant
- Transaction N→1 InstallmentPlan (optional)

### File Organization
```
fin/                       # Main package
├── extractors/           # PDF parsers (one per bank)
├── classification/       # 3-tier classification system
├── models/               # SQLAlchemy ORM models
├── reports/              # Report generation (monthly, commitments)
├── vectorization/        # ChromaDB indexing pipeline
├── rag/                  # RAG retrieval + chat engine
├── analysis/             # Subscriptions, patterns detection
├── export/               # CSV/JSON exporters
├── alerts/               # Financial alerts detection
└── utils/                # Date/money parsing, text normalization

data/                     # Local data (gitignored)
├── inbox/               # PDFs to process (organized by YYYY/MM)
├── processed/           # Archived PDFs
├── reports/             # Generated markdown reports
├── exports/             # CSV/JSON exports
└── finbot.db            # SQLite database
```

## Important Implementation Details

### PDF Processing Error Handling
The system handles partial extraction failures gracefully:
- Location: `fin/cli.py:89-130`
- If statement extraction fails but transactions succeed, creates minimal statement
- Only marks as 'success' if transactions OR valid period extracted
- Logs all failures to `processing_log` table with detailed error messages

**Do not break this behavior** - production relies on partial extraction recovery.

### Duplicate & Reversal Detection
After processing, the system auto-detects:
- Duplicates: Same merchant, amount, ±3 days
- Reversals: Same merchant, negated amount, ±30 days

Location: `fin/utils/duplicates.py`
Runs automatically after each PDF process (see `fin/cli.py:178-184`)

### LLM Context Restrictions
The LLM classifier is **restricted to Mexican context** via system prompt:
- Location: `fin/classification/llm_classifier.py`
- Categories are Mexican-specific (see `docs/CATEGORIES.md`)
- This prevents hallucination of US/international categories

**When modifying categories**: Update both `fin/config/rules.yaml` AND the LLM system prompt.

### OCR Support (Liverpool Bank)
Liverpool requires OCR due to image-based PDFs:
- Dependencies: `tesseract-ocr`, `pytesseract`, `pdf2image`
- Location: `fin/extractors/liverpool.py`
- Test with: `pytest tests/test_extractors/test_liverpool.py`

If OCR tests fail, check: `tesseract --version` and `which tesseract`

### Database Initialization
The database auto-initializes on first CLI command:
- Location: `fin/models/database.py:init_db()`
- Called from: `fin/cli.py:25`
- Migration strategy: Currently schema updates via manual ALTER TABLE (no Alembic yet)

**Adding new columns**: Update model → manually ALTER existing DBs → add migration docs.

### Vector Store Persistence
ChromaDB persists to disk automatically:
- Default location: `./data/chromadb/`
- Collection name: `finanzas_docs`
- Configured in: `fin/vectorization/vector_store.py:20-30`

**Do not delete** `data/chromadb/` without backup - it requires full re-indexing (slow).

## Testing Strategy

### Test Organization
- `tests/test_extractors/`: Bank parser tests (requires test PDFs)
- `tests/test_classification/`: Classification system tests
- `tests/test_models/`: Database model tests
- `tests/test_utils/`: Utility function tests
- `tests/fixtures/`: Sample PDFs and data
- `tests/integration/`: End-to-end pipeline tests

### Running Tests Without PDFs
Some tests require actual bank PDFs which are gitignored. If missing:
```bash
# Skip PDF-dependent tests
pytest tests/ -v --ignore=tests/test_extractors/test_bbva.py
```

### Test Database
Tests use isolated database:
- Location: Temporary file (see `tests/conftest.py`)
- Fixture: `session` (auto-cleanup after each test)
- Never modifies production `data/finbot.db`

## Configuration Files

- `config/settings.yaml`: Database path, logging config
- `fin/config/rules.yaml`: Classification regex rules (critical - frequently updated)
- `environment.yml`: Conda environment specification
- `pyproject.toml`: Build config, pytest settings, coverage config

## External Dependencies

### Critical Services
1. **Ollama** (required for LLM features):
   - Service: `sudo systemctl start ollama`
   - Model: `ollama pull qwen2.5:7b`
   - Health check: `fin/rag/chat_engine.py:health_check()`

2. **Tesseract OCR** (required for Liverpool bank):
   - Install: `sudo apt-get install tesseract-ocr tesseract-ocr-spa`
   - Test: `tesseract --version`

### All Services Offline Mode
The system gracefully degrades without external services:
- No Ollama → LLM classification disabled, rules-only mode
- No Tesseract → Liverpool bank unsupported
- Both available → Full functionality

## Common Issues & Solutions

### "fin command not found"
```bash
conda activate finbot
pip install --force-reinstall -e .
```

### "Ollama connection failed"
```bash
sudo systemctl start ollama
ollama list  # verify qwen2.5:7b is installed
```

### "No transactions extracted" but PDF looks valid
- Check bank detection: Open `fin/extractors/detector.py`
- Add debug prints in parser: `fin/extractors/{bank}.py`
- Run with: `pytest tests/test_extractors/test_{bank}.py -v -s`

### Classification not learning from corrections
- Verify merchant record exists: `SELECT * FROM merchants WHERE normalized_name = 'MERCHANT_NAME';`
- Check category was saved: Merchant table should have category/subcategory populated
- Classification order: Merchant history → Rules → LLM (see `fin/classification/classifier.py:96-112`)

## Development Guidelines

### Code Style
- Follow existing patterns in each module
- Use type hints where possible (not strictly enforced)
- SQLAlchemy models: Define relationships explicitly
- CLI commands: Use Click with Rich for terminal output

### Adding New CLI Commands
Pattern (see `fin/cli.py`):
```python
@cli.command()
@click.option('--month', help='Month YYYY-MM')
def mycommand(month):
    """Command description."""
    session = get_session()
    try:
        # ... implementation
    finally:
        session.close()
```

### Error Handling Philosophy
- CLI: Catch exceptions, display user-friendly errors via Rich console
- Extractors: Return None for failures, log to processing_log
- Classification: Graceful degradation (unclassified transactions are OK)
- RAG: Never crash chat session, show error messages inline

### Database Transactions
Always use the session pattern:
```python
session = get_session()
try:
    # ... operations
    session.commit()
except Exception as e:
    session.rollback()
    raise
finally:
    session.close()
```

## Production Considerations

This codebase is actively used in production for monthly financial processing. When making changes:

1. **Never break PDF processing**: Users rely on monthly statement imports
2. **Preserve classification history**: Merchant learning is critical (user has manually corrected hundreds of transactions)
3. **Maintain data folder structure**: `data/inbox/YYYY/MM/` is expected by automation
4. **Test with real PDFs before deployment**: Unit tests don't catch all PDF parsing edge cases
5. **Backward compatibility for database**: No destructive migrations without migration path

## Getting Help

- Architecture diagram: `docs/Architecture.md`
- User guide: `docs/USAGE_GUIDE.md`
- Category definitions: `docs/CATEGORIES.md`
- Performance notes: `docs/PERFORMANCE.md`
- Main README: `README.md`
