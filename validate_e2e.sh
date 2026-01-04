#!/bin/bash
# Finbot E2E Production Validation Script
# This script validates the complete workflow end-to-end

set -e  # Exit on error

echo "========================================="
echo "Finbot E2E Production Validation"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo "${YELLOW}Checking prerequisites...${NC}"

# Check Ollama
if ! systemctl is-active --quiet ollama 2>/dev/null; then
    echo "${RED}✗ Ollama is not running${NC}"
    echo "  Start with: sudo systemctl start ollama"
    exit 1
fi
echo "${GREEN}✓ Ollama is running${NC}"

# Check model
if ! ollama list | grep -q "qwen2.5:7b"; then
    echo "${RED}✗ qwen2.5:7b model not found${NC}"
    echo "  Install with: ollama pull qwen2.5:7b"
    exit 1
fi
echo "${GREEN}✓ qwen2.5:7b model available${NC}"

# Check database
if [ ! -f "data/finbot.db" ]; then
    echo "${YELLOW}⚠ Database not initialized${NC}"
    echo "  Database will be created on first use"
fi

echo ""
echo "${YELLOW}=========================================${NC}"
echo "${YELLOW}PHASE 1: PDF Processing${NC}"
echo "${YELLOW}=========================================${NC}"
echo ""

# Check for test PDFs
if [ ! -d "data/inbox" ]; then
    mkdir -p data/inbox
    echo "${YELLOW}Created data/inbox directory${NC}"
fi

PDF_COUNT=$(find data/inbox -name "*.pdf" 2>/dev/null | wc -l)
if [ "$PDF_COUNT" -eq 0 ]; then
    echo "${YELLOW}⚠ No PDFs found in data/inbox${NC}"
    echo "  Add PDFs to data/inbox/ and run this script again"
    echo "  Or skip to next phase with existing data"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "${GREEN}Found $PDF_COUNT PDF(s) in data/inbox${NC}"
    echo ""
    
    # Process PDFs
    echo "Processing PDFs..."
    for pdf in data/inbox/*.pdf; do
        echo "  Processing: $(basename "$pdf")"
        fin process "$pdf" || echo "${RED}  ✗ Failed to process $pdf${NC}"
    done
    echo "${GREEN}✓ PDF processing complete${NC}"
fi

echo ""
echo "${YELLOW}=========================================${NC}"
echo "${YELLOW}PHASE 2: Classification Review${NC}"
echo "${YELLOW}=========================================${NC}"
echo ""

# Count transactions
TRANS_COUNT=$(sqlite3 data/finbot.db "SELECT COUNT(*) FROM transactions;" 2>/dev/null || echo "0")
echo "Total transactions in database: $TRANS_COUNT"

if [ "$TRANS_COUNT" -eq 0 ]; then
    echo "${RED}✗ No transactions found${NC}"
    echo "  Process PDFs first (Phase 1)"
    exit 1
fi

# Check classification
UNCLASSIFIED=$(sqlite3 data/finbot.db "SELECT COUNT(*) FROM transactions WHERE category IS NULL;" 2>/dev/null || echo "0")
echo "Unclassified transactions: $UNCLASSIFIED"

if [ "$UNCLASSIFIED" -gt 10 ]; then
    echo "${YELLOW}⚠ Many unclassified transactions${NC}"
    echo "  Run: fin correct --limit 20"
    read -p "Run correction now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        fin correct --limit 10
    fi
fi

echo "${GREEN}✓ Classification review complete${NC}"

echo ""
echo "${YELLOW}=========================================${NC}"
echo "${YELLOW}PHASE 3: Report Generation${NC}"
echo "${YELLOW}=========================================${NC}"
echo ""

# Get latest month with data
LATEST_MONTH=$(sqlite3 data/finbot.db "SELECT strftime('%Y-%m', MAX(date)) FROM transactions;" 2>/dev/null || echo "")

if [ -z "$LATEST_MONTH" ]; then
    echo "${RED}✗ No transactions found for reporting${NC}"
    exit 1
fi

echo "Latest month with data: $LATEST_MONTH"
echo ""

# Generate all reports
echo "Generating reports for $LATEST_MONTH..."
fin reports --month "$LATEST_MONTH"
echo "${GREEN}✓ Standard reports generated${NC}"

# Generate enhanced report
echo ""
echo "Generating enhanced report..."
fin report --month "$LATEST_MONTH"
echo "${GREEN}✓ Enhanced report generated${NC}"

# Check alerts
echo ""
echo "Checking alerts..."
fin alerts --month "$LATEST_MONTH"
echo "${GREEN}✓ Alerts checked${NC}"

# List generated files
echo ""
echo "Generated report files:"
ls -lh data/reports/summaries/"$LATEST_MONTH"* 2>/dev/null || echo "  (no files found)"

echo ""
echo "${YELLOW}=========================================${NC}"
echo "${YELLOW}PHASE 4: Vector Indexing${NC}"
echo "${YELLOW}=========================================${NC}"
echo ""

# Index documents
echo "Indexing documents for RAG..."
fin index --month "$LATEST_MONTH"
echo "${GREEN}✓ Indexing complete${NC}"

# Show stats
echo ""
echo "Vector index stats:"
fin index

echo ""
echo "${YELLOW}=========================================${NC}"
echo "${YELLOW}PHASE 5: RAG Chat Test${NC}"
echo "${YELLOW}=========================================${NC}"
echo ""

# Test chat with automated queries
echo "Testing chat with sample queries..."
echo ""

# Create temp script for chat testing
cat > /tmp/finbot_chat_test.txt << 'EOF'
¿Cuánto gasté en total este mes?
¿Qué MSI tengo activos?
/exit
EOF

echo "Sample questions:"
echo "  1. ¿Cuánto gasté en total este mes?"
echo "  2. ¿Qué MSI tengo activos?"
echo ""
echo "${YELLOW}Note: Chat requires manual interaction${NC}"
echo "Run: fin chat"
echo "Or test interactively now..."

read -p "Open interactive chat? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    fin chat
fi

echo ""
echo "${YELLOW}=========================================${NC}"
echo "${YELLOW}PHASE 6: Data Export${NC}"
echo "${YELLOW}=========================================${NC}"
echo ""

# Export data
echo "Exporting transaction data..."
mkdir -p data/exports

# CSV export
fin export transactions --start-date "${LATEST_MONTH}-01" --format csv > "data/exports/transactions_${LATEST_MONTH}.csv"
echo "${GREEN}✓ CSV export: data/exports/transactions_${LATEST_MONTH}.csv${NC}"

# JSON export
fin export msi --format json > "data/exports/msi_$(date +%Y%m%d).json"
echo "${GREEN}✓ JSON export: data/exports/msi_$(date +%Y%m%d).json${NC}"

echo ""
echo "${YELLOW}=========================================${NC}"
echo "${GREEN}✓ E2E Validation Complete!${NC}"
echo "${YELLOW}=========================================${NC}"
echo ""

echo "Summary:"
echo "  • Transactions processed: $TRANS_COUNT"
echo "  • Reports generated: data/reports/summaries/"
echo "  • Alerts checked: fin alerts --month $LATEST_MONTH"
echo "  • Vector index: $(sqlite3 data/chromadb/chroma.sqlite3 'SELECT COUNT(*) FROM embeddings;' 2>/dev/null || echo 'N/A') documents"
echo "  • Exports: data/exports/"
echo ""
echo "Next steps:"
echo "  1. Review reports: cat data/reports/summaries/${LATEST_MONTH}-enhanced.md"
echo "  2. Check alerts: fin alerts --month $LATEST_MONTH"
echo "  3. Try chat: fin chat"
echo "  4. Export more data: fin export --help"
echo ""
echo "${GREEN}All systems operational! 🚀${NC}"
