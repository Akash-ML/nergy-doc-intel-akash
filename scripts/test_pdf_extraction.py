import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.pdf_extractor import extract_pages, PDFExtractionError

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_pdf_extraction.py <path_to_pdf>")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        pages = extract_pages(file_path)
    except PDFExtractionError as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)

    print(f"✅ Extracted {len(pages)} pages from {file_path}")
    for p in pages[:3]:  # preview first 3 pages
        preview = p["text"][:150].replace("\n", " ")
        print(f"  Page {p['page_number']}: {preview}...")

if __name__ == "__main__":
    main()