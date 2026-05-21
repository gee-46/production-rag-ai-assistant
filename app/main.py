from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from docx import Document

from app.services.reranker import rerank
from app.services.loader import load_documents
from app.services.embeddings import get_embedding
from app.services.vector_store import VectorStore
from app.services.chunker import chunk_text
from app.services.context_builder import build_prompt
from app.services.llm import generate_answer


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
# Create / Load Vector Store
# -----------------------------

vector_store = VectorStore(dim=len(embeddings[0]))

loaded = vector_store.load()

if not loaded:

    print("Creating new vector store...")

    vector_store.add(embeddings, all_chunks)

    vector_store.save()

else:

    print("Using existing saved vector store.")


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

    # Retrieve candidate chunks
    results = vector_store.search(query_embedding, k=10)

    print("Applying semantic reranking...")

    # Rerank chunks
    results = rerank(request.query, results, top_k=3)

    print("\nRetrieved Chunks:\n")

    for i, chunk in enumerate(results, start=1):

        print(f"{i}. {chunk[:200]}\n")

    # Build prompt using retrieved chunks
    prompt = build_prompt(results, request.query)

    print("Generating grounded response...")

    # Generate grounded answer
    answer = generate_answer(prompt)

    return {
        "query": request.query,
        "answer": answer,
        "retrieved_chunks": results
    }


# -----------------------------
# Upload Endpoint
# -----------------------------

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    print(f"\nUploaded File: {file.filename}")

    # -----------------------------
    # Handle TXT Files
    # -----------------------------

    if file.filename.endswith(".txt"):

        content = await file.read()

        text = content.decode("utf-8")

    # -----------------------------
    # Handle DOCX Files
    # -----------------------------

    elif file.filename.endswith(".docx"):

        temp_content = await file.read()

        with open("temp.docx", "wb") as f:

            f.write(temp_content)

        doc = Document("temp.docx")

        text = "\n".join(
            [para.text for para in doc.paragraphs]
        )

    else:

        return {
            "error": "Only .txt and .docx files are supported"
        }

    # -----------------------------
    # Chunk Text
    # -----------------------------

    chunks = chunk_text(text)

    print(f"Generated {len(chunks)} chunks")

    # -----------------------------
    # Generate Embeddings
    # -----------------------------

    embeddings = [
        get_embedding(chunk)
        for chunk in chunks
    ]

    # -----------------------------
    # Update Vector Store
    # -----------------------------

    vector_store.add(embeddings, chunks)

    # Save updated vector database
    vector_store.save()

    print("Document added to vector store.")

    return {
        "filename": file.filename,
        "chunks_added": len(chunks),
        "message": "Document uploaded successfully"
    
