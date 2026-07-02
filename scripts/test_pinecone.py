import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from pinecone import Pinecone
from backend.config import settings

def main():
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)
    stats = index.describe_index_stats()
    print(f"✅ Pinecone connection success.")
    print(f"Index stats: {stats}")

if __name__ == "__main__":
    main()
