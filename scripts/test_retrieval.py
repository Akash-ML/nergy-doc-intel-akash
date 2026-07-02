import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.retriever import retrieve

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_retrieval.py '<your question>'")
        sys.exit(1)

    query = sys.argv[1]

    print(f"Query: {query}\n")
    results = retrieve(query)

    print(f"✅ Retrieved {len(results)} chunks\n")
    for r in results:
        preview = r["text"][:150].replace("\n", " ")
        print(f"  Score: {r['score']:.4f} | {r['source_file']} (page {r['page_number']})")
        print(f"    {preview}...")
        print()

if __name__ == "__main__":
    main()