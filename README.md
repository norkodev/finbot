# Finbot - Sistema de Inteligencia Financiera Personal

Financial intelligence system for personal finance management, featuring automated bank statement parsing, transaction classification, and AI-powered insights.

## Features (Sprint 1)

- 📄 **Automated PDF Parsing**: Extract data from BBVA bank statements
- 💳 **Transaction Management**: Track regular transactions and installment plans (MSI)
- 🗃️ **SQLite Database**: Local storage with SQLAlchemy ORM
- 🔄 **Idempotent Processing**: Safely reprocess files without duplicates
- 🎨 **Beautiful CLI**: Rich terminal interface with progress tracking

## Installation

### Prerequisites

- Python 3.9 or higher
- conda (Anaconda or Miniconda)

### Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:norkodev/finbot.git
   cd finbot
   ```

2. **Create conda environment**
   ```bash
   conda env create -f environment.yml
   ```

3. **Activate environment**
   ```bash
   conda activate finbot
   ```

4. **Install package**
   ```bash
   pip install -e .
   ```

5. **Verify installation**
   ```bash
   fin --version
   ```

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
- **Sprint 2**: HSBC Parser + Basic Queries
- **Sprint 3**: Intelligent Classification (Rules + LLM)
- **Sprint 4**: Derived Documents + Vectorization
- **Sprint 5**: RAG + Chat Interface
- **Sprint 6**: Reports + Stabilization

See [ROADMAP.md](ROADMAP.md) for detailed sprint breakdown.

## License

MIT

## Contributing

This is a personal project, but suggestions and feedback are welcome!

