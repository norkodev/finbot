#!/usr/bin/env python3
"""Quick script to verify parsed data."""

from fin.models import get_session, Statement, Transaction, InstallmentPlan

session = get_session()

# Get statement
stmt = session.query(Statement).first()
if stmt:
    print('=== Statement ===')
    print(f'Period: {stmt.period_start} to {stmt.period_end}')
    print(f'Due Date: {stmt.due_date}')
    print(f'Payment No Interest: ${stmt.payment_no_interest}')
    print(f'Minimum Payment: ${stmt.minimum_payment}')
    print(f'Account: ***{stmt.account_number}')
    
    print(f'\n=== Transactions ({len(stmt.transactions)}) ===')
    for i, t in enumerate(stmt.transactions[:10], 1):
        print(f'{i}. {t.date} - {t.description[:40]:40} - ${t.amount:>10.2f} [{t.transaction_type}]')
    
    print(f'\n=== Installment Plans ({len(stmt.installment_plans)}) ===')
    for i, p in enumerate(stmt.installment_plans, 1):
        interest_label = "CON interés" if p.has_interest else "SIN interés"
        print(f'{i}. {p.description[:35]:35} - {p.current_installment:2}/{p.total_installments:2} - ${p.monthly_payment:>8.2f} - {interest_label}')
else:
    print('No statement found')

session.close()
