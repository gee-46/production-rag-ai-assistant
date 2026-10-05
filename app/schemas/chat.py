import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: uuid.UUID | None = None  # omit to start a new conversation
    stream: bool = False


class Citation(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    snippet: str
    score: float


class GroundednessVerdict(BaseModel):
    supported: bool
    unsupported_sentences: list[str] = []
    method: str


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    answer: str
    citations: list[Citation]
    groundedness: GroundednessVerdict
    retrieval_debug: dict
