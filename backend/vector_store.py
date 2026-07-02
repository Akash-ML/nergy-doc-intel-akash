from pinecone import Pinecone
from typing import List, Dict
from backend.config import settings

_pc = Pinecone(api_key=settings.PINECONE_API_KEY)
_index = _pc.Index(settings.PINECONE_INDEX_NAME)


def upsert_chunks(embedded_chunks: List[Dict]) -> int:
    """
    Upserts embedded chunks into Pinecone.
    Each chunk dict must have: chunk_id, embedding, text, source_file, page_number, chunk_index.
    Returns the number of vectors upserted.
    """
    vectors = []
    for chunk in embedded_chunks:
        vectors.append({
            "id": chunk["chunk_id"],
            "values": chunk["embedding"],
            "metadata": {
                "text": chunk["text"],
                "source_file": chunk["source_file"],
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"]
            }
        })

    # Pinecone recommends batching upserts in groups of ~100
    batch_size = 100
    total_upserted = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        _index.upsert(vectors=batch)
        total_upserted += len(batch)

    return total_upserted


def delete_all() -> None:
    """Wipes the entire index. Useful for resetting between test runs."""
    _index.delete(delete_all=True)


def get_stats() -> Dict:
    return _index.describe_index_stats()