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
                    
                    # Display results
                    console.print(f"\n[green]✓ {pdf_file.name}[/green]")
                    console.print(f"  [dim]Bank: {extractor.bank_name.upper()}[/dim]")
                    console.print(f"  [dim]Period: {statement.period_start} to {statement.period_end}[/dim]")
                    console.print(f"  [cyan]✓ Summary extracted[/cyan]")
                    console.print(f"  [cyan]✓ {len(transactions)} transactions[/cyan]")
                    console.print(f"  [cyan]✓ {len(installments)} installment plans[/cyan]")
                    
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


if __name__ == '__main__':
    cli()
