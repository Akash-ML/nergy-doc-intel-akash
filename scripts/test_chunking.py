import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.pdf_extractor import extract_pages, PDFExtractionError
from backend.chunker import chunk_pages

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_chunking.py <path_to_pdf>")
        sys.exit(1)

    file_path = sys.argv[1]
    filename = os.path.basename(file_path)

    try:
        pages = extract_pages(file_path)
    except PDFExtractionError as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)

    chunks = chunk_pages(pages, source_file=filename)

    print(f"✅ Produced {len(chunks)} chunks from {len(pages)} pages")
    print()
    for c in chunks[:3]:
        preview = c["text"][:150].replace("\n", " ")
        print(f"  [{c['chunk_id']}] (page {c['page_number']}, idx {c['chunk_index']})")
        print(f"    {preview}...")
        print()

    # sanity check: confirm overlap is working by checking token counts
    from backend.chunker import _token_len
    lengths = [_token_len(c["text"]) for c in chunks]
    print(f"Chunk token lengths — min: {min(lengths)}, max: {max(lengths)}, avg: {sum(lengths)//len(lengths)}")

if __name__ == "__main__":
    main()
