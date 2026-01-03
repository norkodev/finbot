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
def process(directory, force):
    """
    Process bank statement PDFs from a directory.
    
    DIRECTORY: Path to folder containing PDF bank statements
    """
    console.print(f"\n[bold blue]Processing bank statements from: {directory}[/bold blue]\n")
    
    # Get all PDF files
    pdf_files = list(Path(directory).glob('*.pdf')) + list(Path(directory).glob('*.PDF'))
    
    if not pdf_files:
        console.print("[yellow]No PDF files found in directory.[/yellow]")
        return
    
    detector = BankDetector()
    classifier = TransactionClassifier()
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
                
                # Check if already processed
                if not force:
                    existing = session.query(ProcessingLog).filter_by(file_hash=file_hash).first()
                    if existing:
                        console.print(f"[dim]Skipping {pdf_file.name} (already processed)[/dim]")
                        progress.advance(task)
                        continue
                
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
                    
                    if statement is None:
                        console.print(f"[red]✗ Failed to parse {pdf_file.name}[/red]")
                        _log_processing(session, str(pdf_file), file_hash, extractor.bank_name, 'error', 'Parsing failed')
                        progress.advance(task)
                        continue
                    
                    # Classify transactions
                    classified_count = classifier.classify_batch(session, transactions)
                    
                    # Save to database
                    session.add(statement)
                    session.flush()  # Get statement ID
                    
                    for trans in transactions:
                        trans.statement_id = statement.id
                        session.add(trans)
                    
                    for plan in installments:
                        plan.statement_id = statement.id
                        session.add(plan)
                    
                    # Log processing
                    _log_processing(
                        session,
                        str(pdf_file),
                        file_hash,
                        extractor.bank_name,
                        'success',
                        None,
                        1,
                        len(transactions),
                        len(installments)
                    )
                    
                    session.commit()
                    
                    # Detect duplicates and reversals
                    from fin.utils.duplicates import detect_all
                    detection_results = detect_all(session, statement.id)
                    session.commit()
                    
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
                    _log_processing(session, str(pdf_file), file_hash, extractor.bank_name, 'error', str(e))
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


if __name__ == '__main__':
    cli()

