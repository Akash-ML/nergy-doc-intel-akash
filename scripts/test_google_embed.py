import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import google.generativeai as genai
from backend.config import settings

def main():
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    result = genai.embed_content(
        model=settings.EMBEDDING_MODEL,
        content="This is a test sentence for embedding.",
        output_dimensionality=settings.EMBEDDING_DIM
    )
    vector = result["embedding"]
    print(f"✅ Google embedding success. Dimension: {len(vector)}")
    assert len(vector) == settings.EMBEDDING_DIM, "Dimension mismatch!"

if __name__ == "__main__":
    main()