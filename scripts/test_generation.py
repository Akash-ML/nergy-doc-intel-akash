import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.retriever import retrieve
from backend.generator import generate_answer

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_generation.py '<your question>'")
        sys.exit(1)

    query = sys.argv[1]

    print(f"Query: {query}\n")
    print("Retrieving relevant chunks...")
    chunks = retrieve(query)
    print(f"  -> {len(chunks)} chunks retrieved\n")

    for c in chunks:
        print(f"  [{c['score']:.4f}] {c['source_file']} p{c['page_number']}")

    print("\nGenerating answer...")
    answer = generate_answer(query, chunks)

    print(f"\n✅ Answer:\n{answer}")

if __name__ == "__main__":
    main()