from groq import Groq
from typing import List, Dict
from backend.config import settings

_client = Groq(api_key=settings.GROQ_API_KEY)

SYSTEM_PROMPT = """You are a document intelligence assistant. Answer the user's question using ONLY the provided context excerpts from their documents.

Rules:
- Base your answer strictly on the provided context. Do not use outside knowledge.
- If the context does not contain enough information to answer the question, say so clearly — do not guess or fabricate an answer.
- Be concise and direct.
- Do not mention "the context" or "the excerpts" explicitly in your answer — just answer naturally, as if you know the material."""


def build_prompt(query: str, retrieved_chunks: List[Dict]) -> str:
    context_blocks = []
    for i, chunk in enumerate(retrieved_chunks, start=1):
        context_blocks.append(
            f"[Excerpt {i} — {chunk['source_file']}, page {chunk['page_number']}]\n{chunk['text']}"
        )
    context_text = "\n\n".join(context_blocks)

    return f"""Context:
{context_text}

Question: {query}

Answer:"""


def generate_answer(query: str, retrieved_chunks: List[Dict]) -> str:
    """
    Generates an answer grounded in the retrieved chunks.
    Assumes retrieved_chunks is non-empty — caller is responsible for
    handling the "no relevant chunks" case before calling this.
    """
    user_prompt = build_prompt(query, retrieved_chunks)

    response = _client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,  # low temperature — favor grounded, consistent answers over creativity
    )

    return response.choices[0].message.content