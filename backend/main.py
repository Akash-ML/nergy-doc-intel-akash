import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.pdf_extractor import extract_pages, PDFExtractionError
from backend.chunker import chunk_pages
from backend.embedder import embed_chunks
from backend.vector_store import upsert_chunks
from backend.retriever import retrieve
from backend.generator import generate_answer
from backend.schemas import UploadResponse, AskRequest, AskResponse, SourceChunk

app = FastAPI(title="NERGY Document Intelligence System")

# Allow the frontend (served separately, e.g. via a static file server or file://) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a local demo; would restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "NERGY Document Intelligence System"}


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Write to a temp file since our extractor works off a file path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        pages = extract_pages(tmp_path)
    except PDFExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        os.unlink(tmp_path)  # always clean up the temp file

    chunks = chunk_pages(pages, source_file=file.filename)

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No usable text content found after chunking. The PDF may be mostly images or contain unsupported formatting."
        )

    try:
        embedded_chunks = embed_chunks(chunks)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding service error: {e}")

    try:
        vectors_upserted = upsert_chunks(embedded_chunks)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vector database error: {e}")

    return UploadResponse(
        filename=file.filename,
        pages_extracted=len(pages),
        chunks_created=len(chunks),
        vectors_upserted=vectors_upserted,
        status="success"
    )


@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        retrieved_chunks = retrieve(question)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Retrieval error: {e}")

    if not retrieved_chunks:
        return AskResponse(
            answer="I don't have any documents to search yet. Please upload a PDF first.",
            sources=[]
        )

    try:
        answer = generate_answer(question, retrieved_chunks)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Answer generation error: {e}")

    sources = [
        SourceChunk(
            source_file=c["source_file"],
            page_number=c["page_number"],
            snippet=c["text"][:200],
            score=c["score"]
        )
        for c in retrieved_chunks
    ]

    return AskResponse(answer=answer, sources=sources)