from pydantic import BaseModel
from typing import List


class UploadResponse(BaseModel):
    filename: str
    pages_extracted: int
    chunks_created: int
    vectors_upserted: int
    status: str


class AskRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    source_file: str
    page_number: int
    snippet: str
    score: float


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]