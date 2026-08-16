#!/usr/bin/env python3
"""Test query debug script"""
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '.')

    from rag.retrieval.service import search_with_details

    query = "Which projects does Dr. Surapol Vorapatratorn serve on the supervisory committee for?"
    print(f"\nQuery: {query}\n")

    result = search_with_details(query)

    print("\n" + "="*60)
    print("FINAL RESULT")
    print("="*60)
    print(f"Retrieved: {result.get('retrieved_count')} docs")

