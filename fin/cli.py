"""Command-line interface for finbot."""

import click
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
import os
import hashlib
from pathlib import Path

from fin import __version__
from fin.models import init_db, get_session, ProcessingLog, Statement, Transaction, InstallmentPlan
from fin.extractors import BankDetector
from fin.classification import TransactionClassifier


console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """Finbot - Sistema de Inteligencia Financiera Personal"""
    # Initialize database on first run
    init_db()


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--force', is_flag=True, help='Reprocess already processed files')
@click.option('--skip-llm', is_flag=True, help='Skip LLM classification (use rules only, faster)')
def process(directory, force, skip_llm):
    """
    Process bank statement PDFs from a directory.
    
    DIRECTORY: Path to folder containing PDF bank statements
    """
    console.print(f"\n[bold blue]Processing bank statements from: {directory}[/bold blue]\n")
    
    if skip_llm:
        console.print("[yellow]⚡ LLM classification disabled - using rules only[/yellow]\n")
    
    # Get all PDF files
    pdf_files = list(Path(directory).glob('*.pdf')) + list(Path(directory).glob('*.PDF'))
    
    if not pdf_files:
        console.print("[yellow]No PDF files found in directory.[/yellow]")
        return
    
    detector = BankDetector()
    classifier = TransactionClassifier(use_llm=not skip_llm)
    session = get_session()
    
    total_processed = 0
    total_statements = 0
    total_transactions = 0
    total_installments = 0
    
    try:
        with Progress() as progress:
            task = progress.add_task("[cyan]Processing files...", total=len(pdf_files))
            
            for pdf_file in pdf_files:
                progress.update(task, description=f"[cyan]Processing: {pdf_file.name}")
                
                # Calculate file hash
                file_hash = _calculate_file_hash(str(pdf_file))
                
                # Check if already processed SUCCESSFULLY
                # Only skip if status is 'success' and has transactions
                if not force:
                    existing = session.query(ProcessingLog).filter_by(file_hash=file_hash).first()
                    if existing and existing.processing_status == 'success' and existing.transactions_created > 0:
                        console.print(f"[dim]Skipping {pdf_file.name} (already processed successfully)[/dim]")
                        progress.advance(task)
                        continue
                    elif existing and existing.processing_status != 'success':
                        console.print(f"[yellow]⚠ Re-processing {pdf_file.name} (previous attempt: {existing.processing_status})[/yellow]")
                
                # Detect bank
                extractor = detector.detect(str(pdf_file))
                if not extractor:
                    console.print(f"[red]✗ Could not detect bank for {pdf_file.name}[/red]")
                    _log_processing(session, str(pdf_file), file_hash, None, 'error', 'Bank not detected')
                    progress.advance(task)
                    continue
                
                # Parse file
                try:
                    statement, transactions, installments = extractor.parse(str(pdf_file))
                    
                    # Handle complete failure
                    if statement is None and len(transactions) == 0:
                        console.print(f"[red]✗ Failed to parse {pdf_file.name}[/red]")
                        _log_processing(session, str(pdf_file), file_hash, extractor.bank_name, 'error', 'Parsing failed - no data extracted')
                        progress.advance(task)
                        continue
                    
                    # Handle partial results (statement is None but we have transactions)
                    if statement is None and len(transactions) > 0:
                        console.print(f"[yellow]⚠ Partial extraction for {pdf_file.name}[/yellow]")
                        # Create minimal statement
                        from datetime import date
                        statement = Statement()
                        statement.bank = extractor.bank_name
                        statement.source_type = "unknown"
                        statement.source_file = str(pdf_file)
                        statement.period_start = date.today()
                        statement.period_end = date.today()
                    
                    # Validate statement has minimum required data
                    if not statement.bank or not statement.source_file:
                        console.print(f"[red]✗ Invalid statement data for {pdf_file.name}[/red]")
                        _log_processing(session, str(pdf_file), file_hash, extractor.bank_name, 'error', 'Invalid statement data')
                        progress.advance(task)
                        continue
                    
                    # Additional validation: verify we have meaningful data
                    # A valid statement should have either:
                    # 1. Transactions, OR
                    # 2. A valid period (for zero-transaction months - rare but possible)
                    has_valid_period = statement.period_start and statement.period_end
                    
                    if len(transactions) == 0 and not has_valid_period:
                        console.print(f"[yellow]⚠ Warning: No transactions and no period for {pdf_file.name}[/yellow]")
                        console.print(f"[yellow]  This may indicate extraction failure. Logging as partial failure.[/yellow]")
                        _log_processing(session, str(pdf_file), file_hash, extractor.bank_name, 'partial_failure', 
                                      f'No transactions extracted and no valid period', 0, 0, 0)
                        progress.advance(task)
                        continue
                    
                    # Classify transactions
                    try:
                        classified_count = classifier.classify_batch(session, transactions)
                    except Exception as e:
                        console.print(f"[yellow]⚠ Classification failed: {e}[/yellow]")
                        classified_count = 0
                        # Continue - classification failure shouldn't prevent saving
                    
                    # Save to database
                    session.add(statement)
                    session.flush()  # Get statement ID
                    
                    for trans in transactions:
                        trans.statement_id = statement.id
                        session.add(trans)
                    
                    for plan in installments:
                        plan.statement_id = statement.id
                        session.add(plan)
                    
                    # Final validation before marking as success
                    # Only mark as 'success' if we actually extracted data
                    if len(transactions) > 0 or (len(installments) > 0) or has_valid_period:
                        status = 'success'
                        error_msg = None
                    else:
                        # Edge case: shouldn't reach here due to earlier check, but be defensive
                        status = 'partial_success'
                        error_msg = 'Extraction completed but no transactions found'
                    
                    # Log processing
                    _log_processing(
                        session,
                        str(pdf_file),
                        file_hash,
                        extractor.bank_name,
                        status,
                        error_msg,
                        1,
                        len(transactions),
                        len(installments)
                    )
                    
                    session.commit()
                    
                    # Detect duplicates and reversals
                    try:
                        from fin.utils.duplicates import detect_all
                        detection_results = detect_all(session, statement.id)
                        session.commit()
                    except Exception as e:
                        console.print(f"[dim]Warning: Duplicate detection failed: {e}[/dim]")
                        detection_results = {'total_flagged': 0, 'duplicates': 0, 'reversals': 0}
                    
                    # Display results
                    console.print(f"\n[green]✓ {pdf_file.name}[/green]")
                    console.print(f"  [dim]Bank: {extractor.bank_name.upper()}[/dim]")
                    console.print(f"  [dim]Period: {statement.period_start} to {statement.period_end}[/dim]")
                    console.print(f"  [cyan]✓ Summary extracted[/cyan]")
                    console.print(f"  [cyan]✓ {len(transactions)} transactions ({classified_count} classified)[/cyan]")
                    console.print(f"  [cyan]✓ {len(installments)} installment plans[/cyan]")
                    if detection_results['total_flagged'] > 0:
                        console.print(f"  [yellow]⚠ {detection_results['duplicates']} duplicates, {detection_results['reversals']} reversals flagged[/yellow]")
                    
                    total_processed += 1
                    total_statements += 1
                    total_transactions += len(transactions)
                    total_installments += len(installments)
                    
                except Exception as e:
                    console.print(f"[red]✗ Error processing {pdf_file.name}: {e}[/red]")
                    import traceback
                    traceback.print_exc()
                    _log_processing(session, str(pdf_file), file_hash, extractor.bank_name if extractor else None, 'error', str(e))
                    session.rollback()
                
                progress.advance(task)
        
        # Summary
        console.print(f"\n[bold green]Processing complete![/bold green]")
        console.print(f"[dim]Files processed: {total_processed}[/dim]")
        console.print(f"[dim]Statements: {total_statements}[/dim]")
        console.print(f"[dim]Transactions: {total_transactions}[/dim]")
        console.print(f"[dim]Installment plans: {total_installments}[/dim]\n")
        
    finally:
        session.close()


def _calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def _log_processing(session, file_path, file_hash, bank, status, error_msg=None, 
                    statements=0, transactions=0, installments=0):
    """Log file processing result."""
    log = ProcessingLog()
    log.file_path = file_path
    log.file_hash = file_hash
    log.file_size = os.path.getsize(file_path)
    log.bank_detected = bank
    log.processing_status = status
    log.error_message = error_msg
    log.statements_created = statements
    log.transactions_created = transactions
    log.installments_created = installments
    
    session.add(log)


@cli.command()
@click.option('--month', help='Filter by month (YYYY-MM)')
@click.option('--category', help='Filter by category')
@click.option('--min-amount', type=float, help='Minimum amount')
@click.option('--max-amount', type=float, help='Maximum amount')
@click.option('--limit', type=int, default=50, help='Maximum number of results')
def transactions(month, category, min_amount, max_amount, limit):
    """
    List transactions with optional filters.
    
    Examples:
      fin transactions --month 2025-12
      fin transactions --category comida --min-amount 100
    """
    session = get_session()
    
    try:
        # Build query
        query = session.query(Transaction).join(Statement)
        
        # Apply filters
        if month:
            try:
                year, month_num = month.split('-')
                from datetime import date
                start_date = date(int(year), int(month_num), 1)
                # Get last day of month
                if int(month_num) == 12:
                    end_date = date(int(year) + 1, 1, 1)
                else:
                    end_date = date(int(year), int(month_num) + 1, 1)
                
                query = query.filter(Transaction.date >= start_date, Transaction.date < end_date)
            except ValueError:
                console.print("[red]Invalid month format. Use YYYY-MM[/red]")
                return
        
        if category:
            query = query.filter(Transaction.category == category)
        
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        
        # Order by date descending
        query = query.order_by(Transaction.date.desc())
        
        # Apply limit
        results = query.limit(limit).all()
        
        if not results:
            console.print("\n[yellow]No transactions found matching the criteria.[/yellow]\n")
            return
        
        # Display as table
        table = Table(title=f"Transactions ({len(results)} results)")
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Description", width=45)
        table.add_column("Amount", justify="right", style="green", width=12)
        table.add_column("Type", width=10)
        
        total = 0
        for t in results:
            # Color negative amounts red
            amount_str = f"${t.amount:,.2f}"
            amount_style = "red" if t.amount < 0 else "green"
            
            table.add_row(
                str(t.date),
                t.description[:45],
                f"[{amount_style}]{amount_str}[/{amount_style}]",
                t.transaction_type
            )
            total += float(t.amount)
        
        console.print()
        console.print(table)
        console.print(f"\n[bold]Total: ${total:,.2f}[/bold]\n")
        
    finally:
        session.close()


@cli.command()
@click.option('--month', required=True, help='Month to summarize (YYYY-MM)')
def summary(month):
    """
    Show monthly financial summary.
    
    Example:
      fin summary --month 2025-12
    """
    session = get_session()
    
    try:
        # Parse month
        try:
            year, month_num = month.split('-')
            from datetime import date
            start_date = date(int(year), int(month_num), 1)
            if int(month_num) == 12:
                end_date = date(int(year) + 1, 1, 1)
            else:
                end_date = date(int(year), int(month_num) + 1, 1)
        except ValueError:
            console.print("[red]Invalid month format. Use YYYY-MM[/red]")
            return
        
        # Query transactions for the month
        from sqlalchemy import func
        transactions = session.query(Transaction).join(Statement).filter(
            Transaction.date >= start_date,
            Transaction.date < end_date
        ).all()
        
        if not transactions:
            console.print(f"\n[yellow]No transactions found for {month}[/yellow]\n")
            return
        
        # Calculate summaries
        total_income = sum(float(t.amount) for t in transactions if t.amount < 0 and t.transaction_type == 'payment')
        total_expenses = sum(float(t.amount) for t in transactions if t.amount > 0 and t.transaction_type == 'expense')
        total_interest = sum(float(t.amount) for t in transactions if t.transaction_type == 'interest')
        total_fees = sum(float(t.amount) for t in transactions if t.transaction_type == 'fee')
        
        # MSI payments this month
        msi_payments = sum(float(t.amount) for t in transactions if t.is_installment_payment)
        
        # Display summary
        console.print(f"\n[bold blue]Financial Summary for {month}[/bold blue]\n")
        
        summary_table = Table.grid(padding=(0, 2))
        summary_table.add_column(style="cyan", justify="right")
        summary_table.add_column(style="bold")
        
        summary_table.add_row("Total Expenses:", f"[red]${total_expenses:,.2f}[/red]")
        summary_table.add_row("Total Payments:", f"[green]${abs(total_income):,.2f}[/green]")
        summary_table.add_row("Interest Charged:", f"[yellow]${total_interest:,.2f}[/yellow]")
        summary_table.add_row("Fees:", f"[yellow]${total_fees:,.2f}[/yellow]")
        summary_table.add_row("MSI Payments:", f"${msi_payments:,.2f}")
        summary_table.add_row("", "")
        summary_table.add_row("Net Change:", f"[bold]${total_expenses - abs(total_income):,.2f}[/bold]")
        
        console.print(summary_table)
        console.print()
        
        # Category breakdown (if categorized)
        categorized = [t for t in transactions if t.category and t.transaction_type == 'expense']
        if categorized:
            from collections import defaultdict
            by_category = defaultdict(float)
            for t in categorized:
                by_category[t.category] += float(t.amount)
            
            console.print("[bold]Expenses by Category:[/bold]\n")
            cat_table = Table()
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Amount", justify="right", style="green")
            
            for cat in sorted(by_category.keys(), key=lambda x: by_category[x], reverse=True):
                cat_table.add_row(cat.title(), f"${by_category[cat]:,.2f}")
            
            console.print(cat_table)
            console.print()
        
    finally:
        session.close()


@cli.command()
@click.option('--ending-soon', type=int, help='Show plans ending in N months')
@click.option('--with-interest', is_flag=True, help='Only show plans with interest')
def msi(ending_soon, with_interest):
    """
    List active MSI (installment) plans.
    
    Examples:
      fin msi
      fin msi --ending-soon 3
      fin msi --with-interest
    """
    session = get_session()
    
    try:
        # Query active installment plans
        query = session.query(InstallmentPlan).filter(
            InstallmentPlan.status == 'active'
        )
        
        if with_interest:
            query = query.filter(InstallmentPlan.has_interest == True)
        
        plans = query.order_by(InstallmentPlan.end_date_calculated).all()
        
        if not plans:
            console.print("\n[yellow]No active MSI plans found.[/yellow]\n")
            return
        
        # Filter by ending soon
        if ending_soon:
            from datetime import date, timedelta
            cutoff_date = date.today() + timedelta(days=ending_soon * 30)
            plans = [p for p in plans if p.end_date_calculated and p.end_date_calculated <= cutoff_date]
            
            if not plans:
                console.print(f"\n[yellow]No MSI plans ending in the next {ending_soon} months.[/yellow]\n")
                return
        
        # Display as table
        table = Table(title=f"Active MSI Plans ({len(plans)} total)")
        table.add_column("Description", width=35)
        table.add_column("Progress", justify="center", width=12)
        table.add_column("Payment", justify="right", style="cyan", width=12)
        table.add_column("Pending", justify="right", style="yellow", width=12)
        table.add_column("Interest", justify="center", width=8)
        table.add_column("End Date", style="dim", width=12)
        
        total_pending = 0
        total_monthly = 0
        
        for plan in plans:
            # Calculate remaining payments
            remaining = plan.total_installments - plan.current_installment
            progress = f"{plan.current_installment}/{plan.total_installments}"
            
            interest_indicator = "✓" if plan.has_interest else "✗"
            interest_style = "red" if plan.has_interest else "green"
            
            table.add_row(
                plan.description[:35],
                progress,
                f"${plan.monthly_payment:,.2f}",
                f"${plan.pending_balance:,.2f}",
                f"[{interest_style}]{interest_indicator}[/{interest_style}]",
                str(plan.end_date_calculated) if plan.end_date_calculated else "N/A"
            )
            
            total_pending += float(plan.pending_balance or 0)
            total_monthly += float(plan.monthly_payment or 0)
        
        console.print()
        console.print(table)
        console.print(f"\n[bold]Total Monthly Payment: ${total_monthly:,.2f}[/bold]")
        console.print(f"[bold]Total Pending Balance: ${total_pending:,.2f}[/bold]\n")
        
    finally:
        session.close()



@cli.command()
@click.option('--limit', default=10, help='Maximum transactions to review')
def correct(limit):
    """
    Interactively correct transaction classifications.
    
    Reviews unclassified or low-confidence transactions and allows
    manual categorization. Corrections teach the system for future.
    """
    from fin.cli_correct import correct_transactions
    correct_transactions(limit)


@cli.command()
@click.option('--months-back', default=3, help='Check activity in last N months')
def subscriptions(months_back):
    """
    List active subscriptions and recurring payments.
    
    Detects recurring charges based on merchant, amount, and frequency patterns.
    """
    from fin.analysis import get_active_subscriptions
    
    session = get_session()
    subs = get_active_subscriptions(session, months_back=months_back)
    
    if not subs:
        console.print("[yellow]No subscriptions detected[/yellow]")
        return
    
    # Calculate totals
    total_monthly = sum(s['average_amount'] for s in subs)
    
    # Display table
    table = Table(title=f"Active Subscriptions (last {months_back} months)")
    table.add_column("Merchant", style="cyan")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Frequency", style="yellow")
    table.add_column("Count", justify="right")
    table.add_column("Last Payment", style="dim")
    
    for sub in subs:
        marker = "⭐" if sub['is_known_subscription'] else ""
        table.add_row(
            f"{marker} {sub['merchant_name']}",
            f"${sub['average_amount']:,.2f}",
            sub['frequency'],
            str(sub['count']),
            sub['last_payment'].strftime('%Y-%m-%d')
        )
    
    console.print(table)
    console.print(f"\n[bold]Total Monthly: ${total_monthly:,.2f}[/bold]")
    
    session.close()


@cli.command()
@click.option('--month', help='Month to generate reports for (YYYY-MM)')
def reports(month):
    """
    Generate financial reports (summaries, commitments, merchant profiles).
    
    Generates markdown reports for the specified month or all months.
    """
    from fin.reports import (
        generate_monthly_summary,
        generate_commitments_report,
        generate_merchant_profiles
    )
    from pathlib import Path
    
    session = get_session()
    
    if month:
        # Parse YYYY-MM
        try:
            year, month_num = map(int, month.split('-'))
        except ValueError:
            console.print("[red]Invalid month format. Use YYYY-MM (e.g., 2025-12)[/red]")
            return
        
        console.print(f"\n[bold blue]Generating reports for {month}...[/bold blue]\n")
        
        # Monthly summary
        summary_md = generate_monthly_summary(session, year, month_num)
        summaries_dir = Path("data/reports/summaries")
        summaries_dir.mkdir(parents=True, exist_ok=True)
        summary_file = summaries_dir / f"{month}.md"
        summary_file.write_text(summary_md, encoding='utf-8')
        console.print(f"✓ Monthly summary: {summary_file}")
        
    else:
        console.print("\n[bold blue]Generating all reports...[/bold blue]\n")
    
    # Commitments (always generate, it's month-independent)
    commitments_md = generate_commitments_report(session)
    reports_dir = Path("data/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    commitments_file = reports_dir / "commitments.md"
    commitments_file.write_text(commitments_md, encoding='utf-8')
    console.print(f"✓ Commitments: {commitments_file}")
    
    # Merchant profiles
    profiles = generate_merchant_profiles(session)
    if profiles:
        merchants_dir = Path("data/reports/merchants")
        merchants_dir.mkdir(parents=True, exist_ok=True)
        for merchant_name, profile_md in profiles:
            import re
            safe_name = re.sub(r'[^\w\s-]', '', merchant_name).strip().replace(' ', '_')
            profile_file = merchants_dir / f"{safe_name}.md"
            profile_file.write_text(profile_md, encoding='utf-8')
        console.print(f"✓ Merchant profiles: {len(profiles)} generated")
    
    console.print("\n[green]✓ Reports generated successfully![/green]")
    session.close()


@cli.command()
@click.option('--rebuild', is_flag=True, help='Rebuild entire index from scratch')
@click.option('--month', help='Index specific month (YYYY-MM)')
def index(rebuild, month):
    """
    Manage vector index for semantic search.
    
    Indexes financial documents in ChromaDB for RAG/chat functionality.
    """
    from fin.vectorization import IndexPipeline
    
    session = get_session()
    pipeline = IndexPipeline(session)
    
    if rebuild:
        console.print("\n[bold yellow]Rebuilding entire index...[/bold yellow]\n")
        pipeline.rebuild_index()
        console.print("\n[green]✓ Index rebuilt![/green]")
    
    elif month:
        try:
            year, month_num = map(int, month.split('-'))
        except ValueError:
            console.print("[red]Invalid month format. Use YYYY-MM[/red]")
            return
        
        console.print(f"\n[bold blue]Indexing {month}...[/bold blue]\n")
        pipeline.index_month(year, month_num, force=True)
        pipeline.index_commitments(force=True)
        pipeline.index_merchants(force=True)
        console.print("\n[green]✓ Indexing complete![/green]")
    
    else:
        # Show stats
        stats = pipeline.vector_store.get_stats()
        console.print("\n[bold]Vector Index Status[/bold]\n")
        console.print(f"Total documents: {stats['total_documents']}")
        console.print(f"Storage: {stats['persist_directory']}")
    
    session.close()


@cli.command()
@click.option('--model', default='qwen2.5:7b', help='Ollama model to use')
@click.option('--top-k', default=5, help='Number of documents to retrieve')
def chat(model, top_k):
    """
    Interactive chat about your finances using AI.
    
    Ask questions in natural language and get answers based on
    your bank statements and financial data using RAG.
    """
    from fin.rag import ChatEngine
    from fin.rag.prompts import get_example_questions
    
    console.print()
    console.print("[bold cyan]💬 Asistente Financiero[/bold cyan]")
    console.print("[dim]Pregúntame sobre tus finanzas personales[/dim]")
    console.print("[dim]Comandos: /exit, /clear, /sources, /examples, /help[/dim]")
    console.print()
    console.print("[yellow]⚠️  Esta información es orientativa. Verifica siempre tus estados de cuenta.[/yellow]")
    console.print()
    
    # Initialize chat engine
    try:
        engine = ChatEngine(model=model, top_k=top_k)
    except Exception as e:
        console.print(f"[red]Error al inicializar chat: {e}[/red]")
        return
    
    # Health check for Ollama
    if not engine.health_check():
        console.print("[red]⚠️  Ollama no está disponible. Asegúrate de que esté corriendo:[/red]")
        console.print("[dim]   sudo systemctl start ollama[/dim]")
        console.print()
        return
    
    last_sources = []
    
    while True:
        try:
            # Get user input
            question = console.input("[bold green]>[/bold green] ")
            
            if not question.strip():
                continue
            
            # Handle special commands
            if question.startswith('/'):
                command = question.lower().strip()
                
                if command == '/exit':
                    console.print("\n👋 [bold]¡Hasta pronto![/bold]\n")
                    break
                
                elif command == '/clear':
                    engine.clear_history()
                    console.print("[dim]✓ Historial de conversación limpiado[/dim]\n")
                    continue
                
                elif command == '/sources':
                    if last_sources:
                        console.print("\n[bold]📄 Fuentes de la última respuesta:[/bold]")
                        for i, source in enumerate(last_sources, 1):
                            month = source['metadata'].get('month', 'N/A')
                            doc_type = source['metadata'].get('doc_type', 'N/A')
                            score = 1.0 - source.get('distance', 0.0) / 2.0
                            console.print(f"  {i}. {doc_type} ({month}) - relevancia: {score:.2f}")
                        console.print()
                    else:
                        console.print("[dim]No hay fuentes disponibles aún[/dim]\n")
                    continue
                
                elif command == '/examples':
                    console.print("\n[bold]Ejemplos de preguntas:[/bold]")
                    for i, example in enumerate(get_example_questions(), 1):
                        console.print(f"  {i}. {example}")
                    console.print()
                    continue
                
                elif command == '/help':
                    console.print("""
[bold]Comandos disponibles:[/bold]
  /exit      - Salir del chat
  /clear     - Limpiar historial de conversación
  /sources   - Ver fuentes de la última respuesta
  /examples  - Ver ejemplos de preguntas
  /help      - Mostrar esta ayuda

[bold]Ejemplos de preguntas:[/bold]
  - ¿Cuánto gasté en comida en diciembre?
  - ¿Qué compromisos terminan pronto?
  - ¿Cuánto gasto en OXXO al mes?
  - ¿Cuánto he pagado de intereses?
  - Compara mis gastos de noviembre vs diciembre
""")
                    continue
                
                else:
                    console.print(f"[yellow]Comando desconocido: {command}[/yellow]")
                    console.print("[dim]Escribe /help para ver comandos disponibles[/dim]\n")
                    continue
            
            # Process question
            console.print("[dim]🔍 Buscando información...[/dim]")
            
            result = engine.chat(question)
            
            # Display answer
            console.print()
            
            # Format answer with better presentation
            answer = result['answer']
            
            # Check for error
            if result.get('error'):
                console.print(f"[red]{answer}[/red]")
            else:
                # Display answer
                console.print(answer)
            
            # Display sources if any
            if result['sources']:
                console.print()
                console.print("[dim]📄 Fuentes: ", end="")
                
                # Get unique source descriptions
                source_descriptions = []
                for source in result['sources']:
                    month = source['metadata'].get('month', '')
                    doc_type = source['metadata'].get('doc_type', '')
                    
                    doc_type_map = {
                        'summary': 'Resumen',
                        'commitment': 'Compromisos',
                        'merchant_profile': 'Perfil'
                    }
                    doc_type_es = doc_type_map.get(doc_type, doc_type)
                    
                    if month:
                        desc = f"{doc_type_es} {month}"
                    else:
                        desc = doc_type_es
                    
                    if desc not in source_descriptions:
                        source_descriptions.append(desc)
                
                console.print(", ".join(source_descriptions[:3]) + "[/dim]")
                last_sources = result['sources']
            
            console.print()
        
        except KeyboardInterrupt:
            console.print("\n\n👋 [bold]¡Hasta pronto![/bold]\n")
            break
        
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")
            import traceback
            if console.is_terminal:
                traceback.print_exc()


@cli.group()
def export():
    """Export financial data to CSV or JSON."""
    pass


@export.command('transactions')
@click.option('--format', type=click.Choice(['csv', 'json']), default='csv', help='Output format')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--category', help='Filter by category')
@click.option('--bank', help='Filter by bank')
@click.option('--merchant', help='Filter by merchant name')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
def export_transactions(format, start_date, end_date, category, bank, merchant, output):
    """
    Export transactions to CSV or JSON.
    
    Examples:
      fin export transactions --format csv --start-date 2025-12-01 --end-date 2025-12-31
      fin export transactions --category alimentacion --format json -o food.json
      fin export transactions --bank bbva --format csv > bbva.csv
    """
    from fin.export import DataExporter
    from datetime import datetime
    
    session = get_session()
    exporter = DataExporter(session)
    
    # Parse dates
    start_date_obj = None
    end_date_obj = None
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            console.print(f"[red]Invalid start date format. Use YYYY-MM-DD[/red]")
            session.close()
            return
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            console.print(f"[red]Invalid end date format. Use YYYY-MM-DD[/red]")
            session.close()
            return
    
    # Export
    try:
        result = exporter.export_transactions(
            format=format,
            start_date=start_date_obj,
            end_date=end_date_obj,
            category=category,
            bank=bank,
            merchant=merchant
        )
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(result)
            console.print(f"[green]✓ Exported to {output}[/green]")
        else:
            # Output to stdout
            print(result)
    
    except Exception as e:
        console.print(f"[red]Error exporting: {e}[/red]")
    
    session.close()


@export.command('msi')
@click.option('--format', type=click.Choice(['csv', 'json']), default='csv', help='Output format')
@click.option('--status', type=click.Choice(['active', 'completed', 'all']), default='active', help='Filter by status')
@click.option('--output', '-o', type=click.Path(), help='Output file (default: stdout)')
def export_msi(format, status, output):
    """
    Export installment plans (MSI) to CSV or JSON.
    
    Examples:
      fin export msi --format csv --status active
      fin export msi --format json --status all -o msi_all.json
    """
    from fin.export import DataExporter
    
    session = get_session()
    exporter = DataExporter(session)
    
    try:
        result = exporter.export_msi(
            format=format,
            status=status
        )
        
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(result)
            console.print(f"[green]✓ Exported to {output}[/green]")
        else:
            # Output to stdout
            print(result)
    
    except Exception as e:
        console.print(f"[red]Error exporting: {e}[/red]")
    
    session.close()


if __name__ == '__main__':
    cli()

