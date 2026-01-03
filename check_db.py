from fin.models import get_session, Merchant, Transaction

session = get_session()
merchants = session.query(Merchant).all()

print(f"Total Merchants: {len(merchants)}")
for m in merchants:
    print(f"- {m.name} (Norm: {m.normalized_name}) -> {m.category}/{m.subcategory}")

print("\nSample Transactions:")
transactions = session.query(Transaction).limit(10).all()
for t in transactions:
    print(f"- {t.description[:30]}... -> Type: {t.transaction_type} | Category: {t.category}")
