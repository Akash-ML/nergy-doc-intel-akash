import fitz  # PyMuPDF
from typing import List, Dict


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be parsed or contains no extractable text."""
    pass


def extract_pages(file_path: str) -> List[Dict]:
    """
    Extracts text from a PDF, page by page.

    Returns a list of dicts:
        [{"page_number": 1, "text": "..."}, {"page_number": 2, "text": "..."}, ...]

    Raises PDFExtractionError if the file can't be opened or has no extractable text.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise PDFExtractionError(f"Could not open PDF: {e}")

    if doc.page_count == 0:
        doc.close()
        raise PDFExtractionError("PDF has no pages.")

    pages = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text().strip()
        pages.append({
            "page_number": page_num + 1,  # 1-indexed for human-readable citations
            "text": text
        })

    doc.close()

    total_text_length = sum(len(p["text"]) for p in pages)
    if total_text_length == 0:
        raise PDFExtractionError(
            "No extractable text found in PDF. It may be a scanned/image-only document."
        )

    return pages


def extract_pages_from_bytes(file_bytes: bytes, filename: str = "uploaded.pdf") -> List[Dict]:
    """
    Same as extract_pages, but accepts raw bytes (useful for FastAPI UploadFile).
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise PDFExtractionError(f"Could not open PDF '{filename}': {e}")

    if doc.page_count == 0:
        doc.close()
        raise PDFExtractionError(f"PDF '{filename}' has no pages.")

    pages = []
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text().strip()
        pages.append({
            "page_number": page_num + 1,
            "text": text
        })

    doc.close()

    total_text_length = sum(len(p["text"]) for p in pages)
    if total_text_length == 0:
        raise PDFExtractionError(
            f"No extractable text found in '{filename}'. It may be a scanned/image-only document."
        )

    return pages