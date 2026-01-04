# Finbot - Sistema de Inteligencia Financiera Personal

Financial intelligence system for personal finance management, featuring automated bank statement parsing, transaction classification, and AI-powered insights.

## Features

- 📄 **Automated PDF Parsing**: Support for **7 banks** (BBVA, HSBC, Banamex, Banorte, Liverpool x2)
  - Standard text extraction for BBVA, HSBC, Banamex, Banorte
  - **OCR support** for Liverpool (pytesseract + pdf2image)
- 💳 **Transaction Management**: Track regular transactions, installment plans, and balance transfers
- 🧠 **AI Classification**: 3-tier classification system (History → Rules → LLM)
  - **Local LLM**: Uses Ollama + Qwen2.5 restricted to Mexican context
  - **Interactive Learning**: Teach the system with `fin correct`
- 📅 **Subscription Detection**: Automatically finds recurring monthly payments
- 📊 **Financial Reports**: Auto-generated markdown reports
  - Monthly summaries with category breakdown
  - Future commitments (MSI + subscriptions)
  - Merchant spending profiles
- 🔍 **Semantic Search**: RAG-ready vector search with ChromaDB
  - Local embeddings (sentence-transformers)
  - Document chunking and indexing
  - Metadata filtering
- 💬 **AI Chat Assistant**: Interactive financial Q&A with RAG
  - Natural language questions about your finances
  - Semantic document retrieval
  - Context-aware responses with source citations
  - Financial calculations and projections
  - Guardrails to prevent hallucinations
- 🗃️ **SQLite Database**: Local storage with SQLAlchemy ORM
- 🎨 **Beautiful CLI**: Rich terminal interface with tables and progress tracking
- 📂 **Production Ready**: Organized folder structure by year/month

## Installation

### Prerequisites

- Python 3.9 or higher
- conda (Anaconda or Miniconda)
- Ollama (for AI classification)

### Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:norkodev/finbot.git
   cd finbot
   ```

2. **Create conda environment**
   ```bash
   conda env create -f environment.yml
   conda activate finbot
   ```

3. **Install System Dependencies** (Ubuntu/Debian)
   ```bash
   # OCR support (Liverpool)
   sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils
   
   # Ollama (AI Model)
   curl -fsSL https://ollama.com/install.sh | sh
   ```

4. **Setup AI Model**
   ```bash
   # Start Ollama service
   sudo systemctl start ollama
   
   # Download model (4.7 GB)
   ollama pull qwen2.5:7b
   ```

5. **Install Python Package**
   ```bash
   pip install -e .
   ```

6. **Verify installation**
   ```bash
   fin --version
   ```

   > **Troubleshooting CLI**: If `fin` command is not found:
   > 1. Ensure conda environment is active: `conda activate finbot`
   > 2. Reinstall editable package: `pip install --force-reinstall -e .`
   > 3. Check ~/.local/bin is in your PATH


## Usage

### Processing Bank Statements

Place your PDF bank statements in a folder (e.g., `data/statements/`) and run:

```bash
fin process data/statements/
```

The command will:
- Automatically detect the bank (BBVA supported in Sprint 1)
- Extract summary information, transactions, and MSI plans
- Store data in SQLite database (`data/database/finanzas.db`)
- Display progress and results

#### Options

- `--force`: Reprocess files that have already been processed

```bash
fin process data/statements/ --force
```

### Example Output

```
Processing bank statements from: data/statements/

✓ BBVA_TDC_Dic2025.pdf
  Bank: BBVA
  Period: 2025-12-01 to 2025-12-31
  ✓ Summary extracted
  ✓ 18 transactions
  ✓ 5 installment plans

Processing complete!
Files processed: 1
Statements: 1
Transactions: 18
Installment plans: 5
```

### Production Workflow

For recurring monthly processing:

```
finbot/
├── data/
│   ├── inbox/                   # PDFs to process
│   │   └── YYYY/
│   │       └── MM/             # e.g., 2025/12/
│   │           ├── bbva_YYYY-MM.pdf
│   │           ├── hsbc_YYYY-MM.pdf
│   │           └── ...
│   ├── processed/               # Archived PDFs
│   ├── reports/                 # Generated reports
│   ├── exports/                 # Exported data
│   └── finbot.db                # SQLite database
└── validate_e2e.sh              # E2E validation script
```
              # E2E validation script
```

#### Monthly Routine

1. **Organize PDFs**: `mkdir -p data/inbox/$(date +%Y/%m)` and move PDFs there
2. **Run E2E**: Execute `./validate_e2e.sh` for automated validation
3. **Or Manual**: `fin process data/inbox/2025/12/`, review with `fin correct`, generate reports
4. **Archive**: Move processed PDFs to `data/processed/2025/12/`

#### Estimated Cut-off Dates
*   **HSBC, Banamex Joy, Banorte**: ~15-17th of the month (Process on the 20th)
*   **BBVA, Banamex Clásica**: ~19-20th of the month (Process on the 25th)
*   **Liverpool**: Variable

#### Automation
You can set up a cron job to check for new files periodically:

```bash
0 9 20 * * /path/to/process_monthly.sh
```

### Querying Data

Finbot provides powerful commands to explore your financial data:

#### 1. List Transactions
View transactions with optional filters:

```bash
# View transactions for a specific month
fin transactions --month 2025-12

# Filter by category (future feature) or amount
fin transactions --min-amount 1000 --limit 10
```

#### 2. Monthly Summary
Get a high-level overview of your finances for a month:

```bash
fin summary --month 2025-12
```
Displays total expenses, payments, interest charged, fees, and MSI payments.

#### 3. Installment Plans (MSI)
Track your active installment plans and balance transfers:

```bash
# List all active plans
fin msi

# Show plans ending in the next 3 months
fin msi --ending-soon 3
```

#### 4. Generate Financial Reports
Create markdown reports for analysis:

```bash
# Generate reports for specific month
fin reports --month 2025-12

# Generate all reports (commitments + merchant profiles)
fin reports
```

Reports are saved to `data/reports/`:
- `summaries/YYYY-MM.md`: Monthly financial summary
- `commitments.md`: Active MSI and subscriptions
- `merchants/*.md`: Spending profiles per merchant

#### 5. Manage Vector Index
Index documents for semantic search (RAG):

```bash
# Rebuild entire index
fin index --rebuild

# Index specific month
fin index --month 2025-12

# View index stats
fin index
```

#### 6. Interactive Classification Correction
Teach the system with manual corrections:

```bash
fin correct --limit 10
```

#### 7. View Subscriptions
See recurring monthly payments:

```bash
fin subscriptions --months-back 3
```

#### 8. AI Chat Assistant
Ask questions about your finances in natural language:

```bash
fin chat
```

**Example Session**:
```
💬 Asistente Financiero

> ¿Cuánto gasté en comida en diciembre?

🔍 Buscando información...

En diciembre 2025 gastaste $8,543 en alimentación,
representando el 22% de tus gastos totales del mes...

📄 Fuentes: Resumen 2025-12

> ¿Qué MSI terminan pronto?

...

> /exit
👋 ¡Hasta pronto!
```

**Available Commands**:
- `/exit` - Exit chat
- `/clear` - Clear conversation history
- `/sources` - Show sources from last answer
- `/examples` - Show example questions
- `/help` - Show help

## Project Structure

```
finbot/
├── fin/                    # Main package
│   ├── cli.py             # CLI commands
│   ├── models/            # SQLAlchemy models
│   ├── extractors/        # PDF parsers
│   └── utils/             # Utility functions
├── config/                # Configuration files
├── data/                  # Data directory (gitignored)
│   ├── database/          # SQLite database
│   └── statements/        # PDF files
├── tests/                 # Unit tests
├── environment.yml        # Conda environment
└── README.md
```

## Development

### Running Tests

```bash
pytest tests/ -v --cov=fin
```

### Database Schema

The system uses SQLite with the following main tables:

- `statements`: Bank statement metadata
- `transactions`: Individual transactions
- `installment_plans`: MSI (Meses Sin Intereses) plans
- `merchants`: Catalog of merchants/stores
- `processing_log`: File processing history

## Roadmap

- **Sprint 1**: ✅ Setup + BBVA Parser
- **Sprint 2**: ✅ HSBC Parser + Basic Queries
- **Sprint 3**: Intelligent Classification (Rules + LLM)
- **Sprint 4**: Derived Documents + Vectorization
- **Sprint 5**: RAG + Chat Interface
- **Sprint 6**: Reports + Stabilization

See [ROADMAP.md](ROADMAP.md) for detailed sprint breakdown.

## License

MIT

## Contributing

This is a personal project, but suggestions and feedback are welcome!

