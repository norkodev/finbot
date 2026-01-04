"""Test script for LLM classifier setup."""

import sys
sys.path.insert(0, '/home/nor/Workspace/finbot')

from fin.classification.llm_classifier import LLMClassifier


def test_ollama_connection():
    """Test if Ollama is running and responding."""
    print("Testing Ollama connection...")
    
    classifier = LLMClassifier(model="qwen2.5:7b")
    
    if classifier.health_check():
        print("✓ Ollama is running and model is available!")
        return True
    else:
        print("✗ Ollama not responding or model not available")
        print("  Make sure to run: ollama pull qwen2.5:7b")
        return False


def test_classification():
    """Test classification with sample transactions."""
    print("\nTesting classification...")
    
    classifier = LLMClassifier(model="qwen2.5:7b")
    
    test_transactions = [
        {
            'id': 1,
            'description': 'NETFLIX.COM',
            'amount': 199.00
        },
        {
            'id': 2,
            'description': 'UBER EATS',
            'amount': 450.50
        },
        {
            'id': 3,
            'description': 'OXXO HDA DEL VALLE',
            'amount': 89.50
        },
        {
            'id': 4,
            'description': 'SMARTFIT MENSUALIDAD',
            'amount': 599.00
        }
    ]
    
    try:
        results = classifier.classify_batch(test_transactions)
        
        print("\nResults:")
        for trans, (category, subcategory, confidence) in zip(test_transactions, results):
            print(f"  {trans['description']:<30} → {category}/{subcategory} ({confidence:.2f})")
        
        return True
    
    except Exception as e:
        print(f"✗ Classification failed: {e}")
        return False


if __name__ == '__main__':
    print("="*60)
    print("Ollama + LLM Classifier Test")
    print("="*60)
    
    # Test 1: Connection
    if not test_ollama_connection():
        print("\n❌ Ollama not available. Please install and start Ollama:")
        print("   1. curl -fsSL https://ollama.com/install.sh | sh")
        print("   2. ollama pull qwen2.5:7b")
        print("   3. ollama serve  # (should start automatically)")
        sys.exit(1)
    
    # Test 2: Classification
    if test_classification():
        print("\n✅ All tests passed! LLM classifier is ready.")
    else:
        print("\n⚠️  Classification test failed, but Ollama is working.")
        sys.exit(1)
