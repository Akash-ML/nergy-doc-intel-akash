# NERGY Document Intelligence System

A web application that ingests PDF documents, answers natural-language questions about their content with page-level citations, and is optimized end-to-end for **low latency**.

---

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack & Why](#tech-stack--why)
- [Setup Instructions](#setup-instructions)
- [Running the Application](#running-the-application)
- [Design Decisions](#design-decisions)
- [Optimization Target: Latency](#optimization-target-latency)
- [Tradeoffs](#tradeoffs)
- [Edge Case Handling](#edge-case-handling)
- [Testing Performed](#testing-performed)
- [What Breaks at Scale](#what-breaks-at-scale)
- [What I'd Improve With More Time](#what-id-improve-with-more-time)
- [Project Structure](#project-structure)

---

## Overview

Users upload one or more PDFs through a simple web UI. The system extracts text, chunks it, embeds it, and stores it in a vector database. Users then ask questions in natural language and receive an answer grounded strictly in the uploaded documents, along with the exact source excerpts (filename + page number) used to generate that answer.

---

## Architecture

```
Browser: HTML/JS/CSS
              (served as static files from FastAPI)
                            │
              ┌─────────────┴──────────────┐
              │                             │
     POST /upload (PDF file)      POST /ask ({ question })
              │                             │
              ▼                             ▼
┌────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                         │
├───────────────────────────────┬────────────────────────────────┤
│  /upload                      │  /ask                          │
│                                │                                │
│  1. Validate file              │  1. Validate question          │
│     (type, size)               │                                │
│  2. PyMuPDF → extract          │  2. Embed query (Google,       │
│     text/page                  │     768-dim, RETRIEVAL_QUERY)  │
│  3. Chunk (500 tok, 75         │  3. Pinecone search top_k=4    │
│     overlap, per-page,         │  4. Filter by relevance        │
│     whitespace-normalized)     │     threshold (0.65)           │
│  4. Embed chunks (Google       │  5. If none pass: return       │
│     gemini-embedding-001,      │     graceful "not found" msg   │
│     768-dim, RETRIEVAL_        │  6. Build grounded prompt      │
│     DOCUMENT, concurrent       │     from retrieved chunks      │
│     via ThreadPoolExecutor)    │  7. Groq (Llama 3.3 70B)       │
│  5. Upsert to Pinecone         │     generates answer           │
│     (id, vector, metadata)     │  8. Return answer + source     │
│                                │     chunks (file, page,        │
│                                │     snippet, score)            │
└───────────────────────────────┴────────────────────────────────┘
              │                             │
              ▼                             ▼
   [Pinecone serverless]          [Google AI Studio / Groq APIs]
   vector store, dim 768,
   cosine similarity

---

## Tech Stack & Why

| Layer | Choice | Why |
|---|---|---|
| Backend framework | FastAPI | Async-native (good fit for I/O-bound external API calls), automatic request validation via Pydantic, free interactive docs at `/docs` for manual testing |
| Frontend | Plain HTML/JS/CSS | No build step, zero tooling overhead — appropriate given the assignment explicitly deprioritizes visual design in favor of function |
| PDF parsing | PyMuPDF (`fitz`) | Fast text extraction, gives reliable per-page text needed for citation accuracy |
| Chunking | Fixed-size (500 tokens, 75 overlap), per-page, `tiktoken`-based | Simple, fast, predictable, and keeps every chunk tied to exactly one page number for unambiguous citations |
| Embeddings | Google `gemini-embedding-001`, output truncated to 768 dimensions via Matryoshka Representation Learning | Free tier, no local model/GPU dependency, avoids cold-start latency risk seen on HuggingFace's free serverless inference tier |
| Vector database | Pinecone (serverless, free tier) | Minimal setup friction, simple SDK, avoids the reliability/scaling limitations of an in-memory-only store while still being fast enough for this scale |
| LLM (generation) | Groq API, Llama 3.3 70B | Groq's custom inference hardware (LPUs) delivers meaningfully faster token generation than typical LLM API latency, directly reinforcing the latency optimization target |
| Retrieval | top_k=4, no reranking | Reranking adds a second model call and more latency; at this document scale, direct embedding similarity is sufficient |
| Citations | Retrieved chunks returned directly alongside the answer (not LLM self-citation) | More reliable and faster than asking the LLM to cite its own sources — citations come straight from what was actually retrieved, not from the model's potentially inaccurate self-report |

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- API keys for: [Groq](https://console.groq.com), [Google AI Studio](https://aistudio.google.com/apikey), [Pinecone](https://app.pinecone.io)
- A Pinecone index created with: `dimension: 768`, `metric: cosine`, serverless

### Installation

```bash
git clone https://github.com/Akash-ML/nergy-doc-intel-akash.git
cd nergy-doc-intel-akash

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key_here
GOOGLE_API_KEY=your_google_key_here
PINECONE_API_KEY=your_pinecone_key_here
PINECONE_INDEX_NAME=your-pinecone_index_name
```

---

## Running the Application

```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 --host 0.0.0.0
```

Open **`http://localhost:8000`** in a browser. The frontend, `/upload`, and `/ask` are all served from this single FastAPI instance — no separate frontend server or CORS configuration needed for local use.

Interactive API docs (useful for manual testing without the UI): **`http://localhost:8000/docs`**

---

## Design Decisions

**Chunking strategy — fixed-size, per-page, with overlap.**
Chunks are capped at 500 tokens with 75 tokens of overlap between consecutive chunks on the same page. Chunking is deliberately restricted to never cross page boundaries, so every chunk maps to exactly one page number — this is what makes citation attribution unambiguous. The tradeoff is a small loss of context for content that spans a page break; semantic/structure-aware chunking would recover this at the cost of implementation complexity and latency, which didn't fit the optimization target.

**Embedding dimension — 768, not the native 3072.**
`gemini-embedding-001` natively outputs 3072-dimensional vectors but supports Matryoshka Representation Learning, which allows truncation to smaller sizes (768, 1536) with minimal semantic quality loss, because the model was trained so the most important signal concentrates in the earlier dimensions. 768 was chosen to minimize network payload size, storage, and Pinecone query compute time — directly supporting the latency target — at a small, acceptable cost to retrieval precision.

**Task-type-aware embeddings.**
Chunks are embedded with `task_type="RETRIEVAL_DOCUMENT"` and queries with `task_type="RETRIEVAL_QUERY"`. Google's embedding model produces different vector representations depending on this declared role, which measurably improves retrieval alignment between queries and their matching content — a free accuracy gain with no latency cost.

**Citations returned directly, not LLM self-citation.**
Rather than instructing the LLM to cite its own sources inline (which requires the model to accurately track and report which excerpt it drew from — a task LLMs perform inconsistently), the system returns the actual chunks retrieved from Pinecone alongside the answer. This is both faster (no extra parsing/verification step) and more trustworthy, since the citation is a direct record of what was fed to the model, not the model's self-report.

**Relevance threshold — empirically determined, not assumed.**
Dense embedding similarity scores don't behave on an intuitive 0–1 "unrelated to identical" scale — due to a property called anisotropy, even completely unrelated text pairs tend to score in a positive baseline range with this model family. Testing on this system's actual data showed irrelevant queries scoring 0.5–0.6 and relevant queries scoring 0.67–0.76. A threshold of **0.65** was set based on this observed gap, rather than picking an arbitrary number.

**In-memory vs. hosted vector store — chose hosted (Pinecone).**
An in-memory numpy-based store would technically be faster for this document scale and would eliminate a network round trip. Pinecone was chosen instead because it's a realistic, production-representative choice that doesn't silently lose all indexed data on every server restart, and its serverless free tier adds negligible latency at this scale while meaningfully improving the "what breaks at scale" story (see below).

---

## Optimization Target: Latency

In an interactive QA tool, response time is a first-class UX metric, not a secondary concern. Users issuing exploratory, multi-turn queries lose trust and abandon a tool faster from a few seconds of lag per query than from a small drop in retrieval precision. Additionally, since every answer here is grounded in retrieved chunks with page-level citations, the user has a built-in verification step, they can check the source themselves. That safety net offsets some of the precision cost of skipping heavier retrieval steps like reranking, making latency the more user-facing bottleneck worth optimizing first, especially within a fixed build window where every added step (reranking, multi-hop retrieval) compounds both latency and implementation risk.
Concretely, latency was prioritized at every layer:   

1. **Generation: Groq, not a standard LLM API.** Groq's LPU-based inference hardware produces substantially faster token generation than typical GPU-based LLM API serving, directly reducing the slowest single step in the pipeline (answer generation).
2. **Embeddings: 768 dimensions, not the native 3072.** Smaller vectors mean smaller network payloads on every upsert and query, and faster similarity computation on Pinecone's side.
3. **Retrieval: top_k=4, no reranking pass.** Reranking (e.g., a cross-encoder pass over a wider candidate set) improves precision but requires an additional model inference step on every query. It was deliberately excluded from the core pipeline to keep the query path to a minimum number of sequential calls: embed query → vector search → generate answer.
4. **Citations returned directly, not self-cited by the LLM.** Avoids a second LLM pass or complex output parsing to extract citation information.
5. **Relevance filtering short-circuits irrelevant queries before generation.** If no retrieved chunk clears the relevance threshold, the system returns immediately without calling Groq at all — the most expensive step in the pipeline is skipped entirely for a meaningful class of queries.

### The honest tradeoff

I chose hosted embeddings (Google) and a hosted vector database (Pinecone) over local or in-memory alternatives, which works against pure latency, since every chunk during ingestion and every query now involves a network round trip to external services, plus two additional points of failure (auth, quota, network reliability) that a fully local pipeline wouldn't have. This was a deliberate tradeoff on my part: I knew local embeddings would be faster, but I judged hosted services to carry lower implementation risk and to be more representative of a realistic, production-shaped system, given the time I had. To offset the latency cost, I added concurrent embedding requests (via **ThreadPoolExecutor**, 8 concurrent workers) during ingestion, since Google's embedding API only accepts one input per request, this parallelizes what would otherwise be a strictly sequential embedding step.

---

## Tradeoffs

| Decision | What was gained | What was given up |
|---|---|---|
| Latency over accuracy target | Simpler pipeline, lower implementation risk, faster responses | No reranking, no multi-hop reasoning for complex questions, moderate retrieval precision ceiling |
| 768-dim embeddings (vs. native 3072) | Smaller payloads, faster search | Slightly reduced semantic precision |
| No reranking | One fewer model call per query, lower latency | Retrieval quality is bounded by raw embedding similarity alone |
| Hosted embeddings + vector DB (vs. local/in-memory) | Production-representative, no local model/GPU dependency, no cold-start risk | Network round-trip latency on every operation, external service dependency |
| Per-page chunking (no cross-page chunks) | Unambiguous page-level citations | Minor context loss at page boundaries |
| Chunks returned directly as citations (not LLM self-citation) | Faster, more trustworthy attribution | No LLM-level synthesis of "which parts of multiple excerpts" contributed to a specific sentence |

---

## Edge Case Handling

- **Empty or corrupt PDF** → returns HTTP 422 with a clear error message; never crashes the server
- **PDF with no extractable text** (e.g., scanned/image-only) → detected at extraction time, returns a descriptive error
- **Non-PDF file upload** → rejected with HTTP 400 before any processing begins
- **Oversized file** (>20MB) → rejected with HTTP 413
- **Empty question** → rejected with HTTP 400
- **Overly long question** (>1000 characters) → rejected with HTTP 400
- **Query with no relevant content in the index** → detected via an empirically-determined relevance threshold (0.65 cosine similarity); returns a graceful "couldn't find relevant information" message instead of a hallucinated answer, and skips the LLM call entirely
- **No documents uploaded yet** → same graceful message path, since retrieval naturally returns nothing
- **Near-empty/whitespace-heavy chunks** (from sparse PDF layouts like tables or headers) → filtered at chunking time via a minimum character-length threshold, preventing low-information vectors from polluting the index
- **Repeated identical upload** → deterministic chunk IDs (`filename::page::chunk_index`) mean re-uploading the same file overwrites existing vectors in place rather than duplicating them

---

## Testing Performed

- All three external service integrations (Groq, Google embeddings, Pinecone) validated independently before building any application logic
- Full pipeline tested standalone (extraction → chunking → embedding → upsert → retrieval → generation) via CLI scripts before wiring into HTTP endpoints
- All edge cases above manually verified via both the interactive `/docs` UI and the actual frontend
- Multi-document upload and cross-document retrieval tested manually
- Fresh-restart full flow: PASS
- Edge cases re-verified in browser UI: PASS

---

## What Breaks at Scale

This system is built for a small-scale demo (1–50 documents) and would need meaningful rework beyond that:

- **In-memory chunk metadata assumptions and single-process architecture** — the current FastAPI app has no concept of multi-tenancy, concurrent users, or job queuing; simultaneous large uploads would block on Python's GIL and the synchronous parts of the ingestion path
- **No incremental/background ingestion** — uploads are processed synchronously within the request; a 50-document batch upload would time out a typical HTTP client. At real scale this needs an async job queue (e.g., Celery/RQ) with upload status polling
- **No deduplication across documents** — identical or near-identical PDFs uploaded under different filenames would be indexed redundantly
- **Retrieval quality ceiling without reranking** — at larger corpus sizes, raw embedding similarity alone becomes less precise; a reranking stage becomes necessary to maintain answer quality
- **No authentication or per-user document isolation** — anyone hitting the API can query any indexed document; a real multi-tenant system needs user-scoped Pinecone namespaces or metadata filtering
- **Groq free-tier rate limits** — would need a paid tier or fallback provider under real production query volume
- **No caching layer** — repeated identical or similar queries re-run the full embed → search → generate pipeline every time; a semantic cache would reduce both cost and latency at scale

---

## What I'd Improve With More Time

- Add an optional reranking pass (cross-encoder) as a toggle-able "accuracy mode," to make the latency/accuracy tradeoff demonstrable side-by-side rather than only described in writing
- Semantic or structure-aware chunking instead of fixed-size, to reduce context fragmentation
- Streaming responses from Groq to the frontend for perceived latency improvement, even where actual generation time is unchanged
- A background job queue for uploads, so large multi-document batches don't block on a single HTTP request
- Basic automated test suite (currently testing was manual, via CLI scripts and the browser)
- Multi-hop retrieval for genuinely multi-part questions that a single top-k retrieval doesn't fully cover

---

## Project Structure

```text
nergy-doc-intel-akash/
├── backend/
│   ├── main.py              # FastAPI app, routes, static file serving
│   ├── config.py            # Environment config, tunable constants
│   ├── schemas.py           # Pydantic request/response models
│   ├── pdf_extractor.py     # PyMuPDF text extraction
│   ├── chunker.py           # Fixed-size chunking with overlap
│   ├── embedder.py          # Google embedding calls (concurrent)
│   ├── vector_store.py      # Pinecone upsert/query/stats
│   ├── retriever.py         # Query embedding + Pinecone search + relevance filtering
│   └── generator.py         # Groq prompt construction + generation
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── scripts/                 # Standalone test/debug scripts used during development
├── requirements.txt
├── .env                     # Not committed — see Setup Instructions
├── .gitignore
├── PROGRESS.md              # Development log
└── README.md
```