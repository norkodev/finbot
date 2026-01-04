"""CLI command for correcting transaction classifications."""

import click
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from sqlalchemy import or_

from fin.models import get_session, Transaction, Merchant


console = Console()


def correct_transactions(limit: int = 10):
    """
    Interactive correction of unclassified or low-confidence transactions.
    
    Args:
        limit: Maximum number of transactions to review
    """
    session = get_session()
    
    # Find transactions that need review
    unclassified = session.query(Transaction).filter(
        or_(
            Transaction.category == None,
            Transaction.classification_confidence < 0.7
        )
    ).order_by(Transaction.date.desc()).limit(limit).all()
    
    if not unclassified:
        console.print("[green]✓ No transactions need review![/green]")
        return
    
    console.print(f"\n[bold]Found {len(unclassified)} transactions to review[/bold]\n")
    
    # Define valid categories
    valid_categories = {
        '1': ('alimentacion', ['supermercado', 'restaurantes', 'delivery', 'cafe']),
        '2': ('transporte', ['rideshare', 'gasolina', 'peaje']),
        '3': ('entretenimiento', ['streaming', 'cine', 'eventos']),
        '4': ('salud', ['farmacia', 'medico', 'gym']),
        '5': ('servicios', ['telefonia', 'internet', 'basicos']),
        '6': ('compras', ['ropa', 'tiendas', 'online']),
        '7': ('gastos_hormiga', ['conveniencia']),
        '8': ('financiero', ['intereses', 'comisiones', 'retiro_efectivo']),
        '9': ('pagos', ['transferencia']),
    }
    
    corrected_count = 0
    
    try:
        for idx, trans in enumerate(unclassified, 1):
            # Show transaction info
            table = Table(show_header=False, border_style="blue")
            table.add_row("[bold]Transaction", f"{idx} of {len(unclassified)}")
            table.add_row("Date", str(trans.date))
            table.add_row("Description", trans.description)
            table.add_row("Amount", f"${trans.amount:,.2f}")
            
            if trans.category:
                table.add_row(
                    "Current",
                    f"{trans.category}/{trans.subcategory} "
                    f"({trans.classification_confidence:.0%} via {trans.classification_source})"
                )
            else:
                table.add_row("Current", "[red]Not classified[/red]")
            
            console.print(table)
            console.print()
            
            # Ask if user wants to classify/reclassify
            if trans.category:
                if not Confirm.ask("Keep current classification?", default=True):
                    needs_classification = True
                else:
                    console.print("[dim]Skipping...[/dim]\n")
                    continue
            else:
                needs_classification = True
            
            if needs_classification:
                # Show categories
                console.print("[bold]Available categories:[/bold]")
                for key, (cat, _) in valid_categories.items():
                    console.print(f"  {key}) {cat}")
                console.print("  0) Skip this transaction")
                
                choice = Prompt.ask("\nSelect category", choices=[str(i) for i in range(10)])
                
                if choice == '0':
                    console.print("[dim]Skipped[/dim]\n")
                    continue
                
                category, subcats = valid_categories[choice]
                
                # Ask for subcategory
                console.print(f"\n[bold]Subcategories for {category}:[/bold]")
                for idx_sub, subcat in enumerate(subcats, 1):
                    console.print(f"  {idx_sub}) {subcat}")
                
                subcat_choice = Prompt.ask(
                    "Select subcategory",
                    choices=[str(i) for i in range(1, len(subcats) + 1)]
                )
                subcategory = subcats[int(subcat_choice) - 1]
                
                # Update transaction
                trans.category = category
                trans.subcategory = subcategory
                trans.classification_source = 'manual_correction'
                trans.classification_confidence = 1.0
                
                # Update merchant (teach for future)
                if trans.merchant_id:
                    merchant = session.query(Merchant).get(trans.merchant_id)
                    if merchant:
                        merchant.category = category
                        merchant.subcategory = subcategory
                        console.print(f"[green]✓ Saved. Future '{merchant.name}' transactions will auto-classify[/green]\n")
                    else:
                        console.print("[green]✓ Saved[/green]\n")
                else:
                    console.print("[green]✓ Saved[/green]\n")
                
                corrected_count += 1
                session.commit()
        
        console.print(f"\n[bold green]✓ Review complete! Corrected {corrected_count} transactions[/bold green]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Saving changes...[/yellow]")
        session.commit()
        console.print(f"[green]✓ Saved {corrected_count} corrections[/green]")
    
    finally:
        session.close()


@click.command()
@click.option('--limit', default=10, help='Maximum transactions to review')
def correct(limit):
    """
    Interactively correct transaction classifications.
    
    Reviews unclassified or low-confidence transactions and allows
    manual categorization. Corrections are saved to merchant catalog
    for automatic future classification.
    """
    correct_transactions(limit)
