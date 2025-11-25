import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.rag_engine import RAGEngine

def test_rag():
    print("="*60)
    print("Testing Advanced RAG Engine")
    print("="*60)
    
    # Initialize RAG
    print("\n1. Initializing RAG Engine...")
    rag = RAGEngine()
    
    # Load knowledge base
    print("2. Loading knowledge base with chunking...")
    rag.load_knowledge_base()
    print("   ✓ Knowledge base loaded")
    
    # Test basic query
    print("\n3. Testing basic query_context...")
    results = rag.query_context("capital preservation")
    print(f"   Found {len(results)} results")
    if results:
        print(f"   First result preview: {results[0][:100]}...")
    
    # Test query_rules
    print("\n4. Testing query_rules...")
    rules = rag.query_rules("stop loss", n=3)
    print(f"   Found {len(rules)} rules")
    for i, rule in enumerate(rules):
        print(f"   Rule {i+1}:")
        print(f"     - Category: {rule['metadata'].get('category', 'N/A')}")
        print(f"     - Priority: {rule['metadata'].get('priority', 'N/A')}")
        print(f"     - Text: {rule['text'][:80]}...")
    
    # Test query with filters
    print("\n5. Testing query_rules with category filter...")
    risk_rules = rag.query_rules("drawdown", category="risk", n=2)
    print(f"   Found {len(risk_rules)} risk-related rules")
    for rule in risk_rules:
        print(f"     - {rule['text'][:100]}...")
    
    # Test query_instructions
    print("\n6. Testing query_instructions...")
    instructions = rag.query_instructions("execution", n=2)
    print(f"   Found {len(instructions)} instructions")
    for inst in instructions:
        print(f"     - {inst['text'][:80]}...")
    
    # Test hybrid_search
    print("\n7. Testing hybrid_search with re-ranking...")
    hybrid_results = rag.hybrid_search("risk management", keywords=["drawdown", "limit"], n=3)
    print(f"   Found {len(hybrid_results)} results (re-ranked)")
    for i, result in enumerate(hybrid_results):
        print(f"   Result {i+1}:")
        print(f"     - Score: {result.get('rerank_score', 0):.3f}")
        print(f"     - Priority: {result['metadata'].get('priority', 'N/A')}")
        print(f"     - Text: {result['text'][:60]}...")
    
    # Test compliance validation
    print("\n8. Testing compliance validation...")
    
    # Test 1: Valid trade
    print("\n   Test 8a: Valid trade (BTC, 1% position)")
    compliance = rag.validate_compliance(
        proposed_action="long BTC",
        asset="BTC",
        position_size=0.01
    )
    print(f"     - Compliant: {compliance['compliant']}")
    print(f"     - Violations: {len(compliance['violations'])}")
    print(f"     - Warnings: {len(compliance['warnings'])}")
    print(f"     - Rules checked: {compliance['total_rules_checked']}")
    
    # Test 2: Oversized position
    print("\n   Test 8b: Oversized position (BTC, 5% position)")
    compliance = rag.validate_compliance(
        proposed_action="long BTC",
        asset="BTC",
        position_size=0.05
    )
    print(f"     - Compliant: {compliance['compliant']}")
    print(f"     - Violations: {len(compliance['violations'])}")
    print(f"     - Warnings: {len(compliance['warnings'])}")
    if compliance['warnings']:
        print(f"     - Warning: {compliance['warnings'][0][:100]}...")
    
    # Test 3: Potentially forbidden asset
    print("\n   Test 8c: Potentially forbidden asset (USDT)")
    compliance = rag.validate_compliance(
        proposed_action="long USDT",
        asset="USDT",
        position_size=0.01
    )
    print(f"     - Compliant: {compliance['compliant']}")
    print(f"     - Violations: {len(compliance['violations'])}")
    if compliance['violations']:
        print(f"     - Violation: {compliance['violations'][0][:100]}...")
    
    print("\n" + "="*60)
    print("RAG Engine Tests Complete!")
    print("="*60)

if __name__ == "__main__":
    test_rag()
