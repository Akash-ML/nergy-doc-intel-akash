# Build Progress Log

## Stack (locked)
- Backend: FastAPI
- Frontend: Plain HTML/JS/CSS
- PDF parsing: PyMuPDF
- Chunking: Fixed 500 tokens, 75 overlap, per-page (chunk_id format: `file::pN::cN`)
- Embeddings: Google gemini-embedding-001, output_dimensionality=768, RETRIEVAL_DOCUMENT/RETRIEVAL_QUERY task types
- Vector DB: Pinecone serverless (index: nergy-doc-intel, dim 768, cosine)
- LLM: Groq (llama-3.3-70b-versatile), temperature=0.2
- Retrieval: top_k=4, no reranking
- Optimization target: Latency

## Steps completed
- [x] Step 0: Repo skeleton, venv, .env, .gitignore
- [x] Step 1: config.py + 3 connectivity smoke tests (Groq, Google, Pinecone) — all passing
- [x] Step 2: backend/pdf_extractor.py — page-level extraction, whitespace-normalized
- [x] Step 3: backend/chunker.py — fixed-size + overlap, MIN_CHUNK_CHARS=20 filter
- [x] Step 4: backend/embedder.py + backend/vector_store.py — concurrent embedding (ThreadPoolExecutor, MAX_WORKERS=8), Pinecone upsert
- [x] Step 5: backend/retriever.py — query embedding + Pinecone search
- [x] Step 6: backend/generator.py — Groq prompt + generation, grounded system prompt
- [x] Step 7: FastAPI endpoints (/upload, /ask)
- [x] Step 8: Edge case handling (relevance threshold: 0.65 based on observed scores, file size limits, input validation)
- [x] Step 9: Frontend (served as static files from FastAPI, single-port setup)
- [x] Step 10: End-to-end testing (Edge cases re-verified in UI, Fresh-restart full flow) 
- [x] Step 11: README
- [ ] Step 12 (future implementation): GPU cross-encoder reranking

## Known issues / notes
- Some whitespace-heavy chunks still slip past MIN_CHUNK_CHARS=20 filter — non-blocking, low priority. Could raise threshold to 40-50 if time allows.
- Relevance score baseline: irrelevant queries scored ~0.5-0.6 (embedding anisotropy, not a bug). Need to note actual relevant-query score range once observed, to set Step 8's threshold.
- gemini-embedding-001 replaced deprecated text-embedding-004; only accepts one input per API call (no true batch endpoint), hence ThreadPoolExecutor for concurrency instead.