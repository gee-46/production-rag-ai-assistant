from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from app.services.loader import load_documents
from app.services.embeddings import get_embedding
from app.services.vector_store import VectorStore
from app.services.chunker import chunk_text
from app.services.context_builder import build_prompt
from app.services.llm import generate_answer
from docx import Document


# -----------------------------
# FastAPI App Initialization
# -----------------------------

app = FastAPI(
    title="Production RAG API",
    description="Retrieval-Augmented Generation system using FAISS + Ollama",
    version="1.0"
)


# -----------------------------
# Load and Prepare Documents
# -----------------------------

docs = load_documents("data/raw_docs")

all_chunks = []

for doc in docs:
    chunks = chunk_text(doc)
    all_chunks.extend(chunks)

print(f"\nTotal chunks loaded: {len(all_chunks)}")


# -----------------------------
# Generate Embeddings
# -----------------------------

embeddings = [get_embedding(chunk) for chunk in all_chunks]


# -----------------------------
# Create Vector Store
# -----------------------------

vector_store = VectorStore(dim=len(embeddings[0]))
vector_store.add(embeddings, all_chunks)

print("Vector store initialized.\n")


# -----------------------------
# Request Schema
# -----------------------------

class QueryRequest(BaseModel):
    query: str


# -----------------------------
# Root Endpoint
# -----------------------------

@app.get("/")
def home():
    return {
        "message": "Production RAG API is running"
    }

# -----------------------------
# Query Endpoint
# -----------------------------

@app.post("/query")
def query_rag(request: QueryRequest):

    print(f"\nUser Query: {request.query}")

    # Convert query into embedding
    query_embedding = get_embedding(request.query)

    # Retrieve top-k similar chunks
    results = vector_store.search(query_embedding, k=4)

    print("\nRetrieved Chunks:\n")

    for i, chunk in enumerate(results, start=1):
        print(f"{i}. {chunk[:200]}\n")

    # Build prompt using retrieved chunks
    prompt = build_prompt(results, request.query)

    # Generate grounded answer
    answer = generate_answer(prompt)

    return {
        "query": request.query,
        "answer": answer,
        "retrieved_chunks": results
    }





