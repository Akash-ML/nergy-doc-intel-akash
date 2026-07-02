from typing import List, Dict
from backend.config import settings
from backend.embedder import embed_query
from backend.vector_store import _index


def retrieve(query: str, top_k: int = None) -> List[Dict]:
    """
    Embeds the query and searches Pinecone for the top-k most relevant chunks.

    Returns a list of dicts:
        [
            {
                "chunk_id": "...",
                "text": "...",
                "source_file": "...",
                "page_number": int,
                "chunk_index": int,
                "score": float
            },
            ...
        ]
    """
    if top_k is None:
        top_k = settings.TOP_K

    query_vector = embed_query(query)

    results = _index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )

    retrieved = []
    for match in results["matches"]:
        metadata = match["metadata"]
        retrieved.append({
            "chunk_id": match["id"],
            "text": metadata["text"],
            "source_file": metadata["source_file"],
            "page_number": metadata["page_number"],
            "chunk_index": metadata["chunk_index"],
            "score": match["score"]
        })

    return retrieved

def retrieve_relevant(query: str, top_k: int = None) -> List[Dict]:
    """
    Same as retrieve(), but filters out chunks below the relevance threshold.
    Used by /ask to avoid answering from weak/irrelevant matches.
    """
    results = retrieve(query, top_k=top_k)
    
    return [r for r in results if r["score"] >= settings.RELEVANCE_THRESHOLD]