import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from backend.config import settings

genai.configure(api_key=settings.GOOGLE_API_KEY)

MAX_WORKERS = 8  # concurrent requests to Google's API


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
    """Embeds a single piece of text. task_type differs for documents vs queries."""
    result = genai.embed_content(
        model=settings.EMBEDDING_MODEL,
        content=text,
        task_type=task_type,
        output_dimensionality=settings.EMBEDDING_DIM
    )
    return result["embedding"]


def embed_query(query: str) -> List[float]:
    """Embeds a search query. Uses RETRIEVAL_QUERY task type for better retrieval matching."""
    return embed_text(query, task_type="RETRIEVAL_QUERY")


def embed_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    Embeds a list of chunk dicts (from chunker.py) concurrently.
    Returns the same chunks with an added "embedding" key.
    Raises the first exception encountered if any embedding call fails.
    """
    results = [None] * len(chunks)

    def _embed_one(index: int, chunk: Dict):
        vector = embed_text(chunk["text"], task_type="RETRIEVAL_DOCUMENT")
        return index, vector

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_embed_one, i, c) for i, c in enumerate(chunks)]
        for future in as_completed(futures):
            index, vector = future.result()  # raises here if that call failed
            results[index] = vector

    embedded_chunks = []
    for chunk, vector in zip(chunks, results):
        embedded_chunks.append({**chunk, "embedding": vector})

    return embedded_chunks