"""Re-classification command for fixing/updating transaction categories."""

import click
from rich.console import Console
from rich.table import Table
from fin.models import get_session, Transaction, Statement
from fin.classification import TransactionClassifier
from datetime import datetime

console = Console()


@click.command()
@click.option('--all', 'reclassify_all', is_flag=True, help='Re-classify all transactions')
@click.option('--month', help='Re-classify specific month (YYYY-MM)')
@click.option('--skip-llm', is_flag=True, help='Use rules only (faster)')
@click.option('--force', is_flag=True, help='Re-classify even if already classified')
@click.option('--unclassified-only', is_flag=True, help='Only classify transactions without category')
def classify_cmd(reclassify_all, month, skip_llm, force, unclassified_only):
    """
    Re-classify transactions using updated rules or LLM.
    
    Examples:
        fin classify --all
        fin classify --month 2025-12
        fin classify --unclassified-only
        fin classify --month 2025-12 --skip-llm
    """
    session = get_session()
    classifier = TransactionClassifier(use_llm=not skip_llm)
    
    console.print()
    console.print(\"[bold cyan]🔄 Re-classifying transactions...[/bold cyan]\")
    if skip_llm:
        console.print(\"[yellow]⚡ LLM disabled - using rules only[/yellow]\")
    console.print()
    
    try:
        # Build query
        query = session.query(Transaction).join(Statement)
        
        # Filter by month if specified
        if month and not reclassify_all:
            try:
                year, month_num = month.split('-')
                from datetime import date
                start_date = date(int(year), int(month_num), 1)
                if int(month_num) == 12:
                    end_date = date(int(year) + 1, 1, 1)
                else:
                    end_date = date(int(year), int(month_num) + 1, 1)
                
                query = query.filter(Transaction.date >= start_date, Transaction.date < end_date)
                console.print(f\"[dim]Filtering by month: {month}[/dim]\\n\")
            except ValueError:
                console.print(\"[red]Invalid month format. Use YYYY-MM[/red]\")
                return
        elif not reclassify_all:
            console.print(\"[yellow]Please specify --all or --month[/yellow]\")
            return
        
        # Filter unclassified only
        if unclassified_only:
            query = query.filter(Transaction.category == None)
            console.print(\"[dim]Only processing unclassified transactions[/dim]\\n\")
        elif not force:
            # If not force, skip already classified
            query = query.filter(Transaction.category == None)
            console.print(\"[dim]Skipping already classified (use --force to re-classify)[/dim]\\n\")
        
        transactions = query.all()
        
        if not transactions:
            console.print(\"[yellow]No transactions to classify[/yellow]\\n\")
            return
        
        console.print(f\"[cyan]Found {len(transactions)} transactions to classify...[/cyan]\\n\")
        
        # Clear existing classifications if force
        if force and not unclassified_only:
            for t in transactions:
                t.category = None
                t.subcategory = None
                t.classification_source = None
                t.classification_confidence = None
        
        # Classify in batches
        classified_count = classifier.classify_batch(session, transactions)
        
        # Count by source
        by_source = {}
        for t in transactions:
            if t.classification_source:
                by_source[t.classification_source] = by_source.get(t.classification_source, 0) + 1
        
        # Commit changes
        session.commit()
        
        # Display results
        console.print(\"\\n[bold green]✓ Classification complete![/bold green]\\n\")
        
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style=\"cyan\", justify=\"right\")
        stats_table.add_column(style=\"bold\")
        
        stats_table.add_row(\"Total transactions:\", str(len(transactions)))
        stats_table.add_row(\"Successfully classified:\", f\"[green]{classified_count}[/green]\")
        stats_table.add_row(\"Unclassified:\", f\"[yellow]{len(transactions) - classified_count}[/yellow]\")
        stats_table.add_row(\"\", \"\")
        
        if by_source:
            stats_table.add_row(\"[bold]By method:[/bold]\", \"\")
            for source, count in sorted(by_source.items()):
                source_label = {
                    'merchant_history': 'Merchant History',
                    'rule_engine': 'Rules',
                    'llm': 'LLM'
                }.get(source, source)
                stats_table.add_row(f\"  {source_label}:\", str(count))
        
        console.print(stats_table)
        console.print()
        
    finally:
        session.close()


if __name__ == '__main__':
    classify_cmd()
