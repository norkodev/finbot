from fin.classification import RuleEngine
from fin.utils import normalize_description

def test_engine():
    engine = RuleEngine()
    print(f"Loaded {len(engine.rules)} rules")
    
    test_cases = [
        "UBER EATS HELADOS",
        "PAGO UBER TRIP HELP.UBER.COM",
        "OXXO HDA DEL VALLE",
        "NETFLIX.COM",
        "FARMACIA SAN PABLO",
        "VIPS TOLUCA CENTRO",
        "PAGO CFE SUMINISTRADOR",
        "NO MATCHING DESCRIPTION",
        "AMAZON MX MARKETPLACE",
    ]
    
    print("\nTesting classification:")
    print("-" * 60)
    print(f"{'Description':<30} | {'Category':<15} | {'Subcategory':<15}")
    print("-" * 60)
    
    for desc in test_cases:
        normalized = normalize_description(desc)
        cat, subcat, conf = engine.classify(normalized)
        print(f"{desc:<30} | {str(cat):<15} | {str(subcat):<15}")

if __name__ == "__main__":
    test_engine()
