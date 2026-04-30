from app.services.loader import load_documents
from app.services.embeddings import get_embedding
from app.services.vector_store import VectorStore
from app.services.llm import generate_answer

# Load docs
docs = load_documents("data/raw_docs")

# Embed docs
embeddings = [get_embedding(doc[:200]) for doc in docs]

# Store
vector_store = VectorStore(dim=len(embeddings[0]))
vector_store.add(embeddings, docs)

