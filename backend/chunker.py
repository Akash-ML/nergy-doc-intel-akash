import tiktoken
from typing import List, Dict
from backend.config import settings

_encoder = tiktoken.get_encoding("cl100k_base")


def _token_len(text: str) -> int:
    return len(_encoder.encode(text))


def _tokens_to_text(tokens: List[int]) -> str:
    return _encoder.decode(tokens)


def chunk_pages(pages: List[Dict], source_file: str) -> List[Dict]:
    """
    Takes extracted pages [{"page_number": int, "text": str}, ...]
    and produces fixed-size, overlapping chunks tagged with metadata.

    Chunking is done per-page (chunks don't cross page boundaries) so that
    every chunk has one unambiguous page number for citation purposes.

    Returns:
        [
            {
                "chunk_id": "source.pdf::p3::c0",
                "text": "...",
                "source_file": "source.pdf",
                "page_number": 3,
                "chunk_index": 0
            },
            ...
        ]
    """
    chunks = []
    global_chunk_index = 0

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        if not text.strip():
            continue  # skip blank pages

        tokens = _encoder.encode(text)
        start = 0
        page_chunk_index = 0

        while start < len(tokens):
            end = min(start + settings.CHUNK_SIZE, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = _tokens_to_text(chunk_tokens).strip()

            MIN_CHUNK_CHARS = 20  # skip chunks with negligible real content
            
            if chunk_text and len(chunk_text) >= MIN_CHUNK_CHARS:
                chunk_id = f"{source_file}::p{page_number}::c{global_chunk_index}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "source_file": source_file,
                    "page_number": page_number,
                    "chunk_index": page_chunk_index
                })
                global_chunk_index += 1
                page_chunk_index += 1

            if end == len(tokens):
                break

            start += settings.CHUNK_SIZE - settings.CHUNK_OVERLAP

    return chunks