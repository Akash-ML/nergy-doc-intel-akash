import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.pdf_extractor import extract_pages, PDFExtractionError
from backend.chunker import chunk_pages
from backend.embedder import embed_chunks
from backend.vector_store import upsert_chunks, get_stats

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_ingestion.py <path_to_pdf>")
        sys.exit(1)

    file_path = sys.argv[1]
    filename = os.path.basename(file_path)

    print(f"Extracting text from {filename}...")
    try:
        pages = extract_pages(file_path)
    except PDFExtractionError as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)
    print(f"  -> {len(pages)} pages extracted")

    print("Chunking...")
    chunks = chunk_pages(pages, source_file=filename)
    print(f"  -> {len(chunks)} chunks created")

    print("Embedding chunks (this calls Google's API concurrently)...")
    embedded_chunks = embed_chunks(chunks)
    print(f"  -> {len(embedded_chunks)} chunks embedded")
    print(f"  -> embedding dimension: {len(embedded_chunks[0]['embedding'])}")

    print("Upserting into Pinecone...")
    count = upsert_chunks(embedded_chunks)
    print(f"  -> {count} vectors upserted")

    print("\nIndex stats after upsert:")
    print(get_stats())

    print(f"\n✅ Full ingestion pipeline succeeded for {filename}")

if __name__ == "__main__":
    main()