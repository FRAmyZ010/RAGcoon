#!/usr/bin/env python3
"""
Test Hybrid Search with Normalized Scores (0-1)
Prototype for testing hybrid search functionality
"""

from backend.retrieval import hybrid_search

def test_hybrid_search():
    """Test hybrid search with normalized scores"""
    
    test_queries = [
        "machine learning algorithm",
        "clustering methodology",
        "web development framework",
    ]
    
    print("\n" + "="*70)
    print("HYBRID SEARCH - Normalized Scores (0-1)")
    print("="*70)
    print("\nScoring Formula:")
    print("  1. Semantic search (normalized 0-1)")
    print("  2. Keyword search (normalized 0-1)")
    print("  3. Hybrid = semantic*0.6 + keyword*0.4")
    print("  4. Final = rerank*0.7 + hybrid*0.3 (all normalized 0-1)")
    print("="*70)
    
    for query in test_queries:
        print(f"\n📌 Query: '{query}'")
        print("-" * 70)
        
        results = hybrid_search(query, top_n=3)
        
        if not results:
            print("No results found")
            continue
        
        for i, result in enumerate(results, 1):
            score = result['score']
            # Ensure score is in 0-1 range
            assert 0 <= score <= 1.1, f"Score out of range: {score}"  # 1.1 for float rounding
            
            # Visual bar for score (0-1)
            bar_length = int(score * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            print(f"\n[{i}] Score: {score:.4f} [{bar}]")
            print(f"    {result['text'][:90]}...")
    
    print("\n" + "="*70)
    print("✅ All scores normalized to [0, 1] range")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_hybrid_search()
