from app.services.loader import load_documents
from app.services.embeddings import get_embedding
from app.services.vector_store import VectorStore
from app.services.chunker import chunk_text
from app.services.context_builder import build_prompt
from app.services.llm import generate_answer

# Load documents
docs = load_documents("data/raw_docs")

# 🔥 Step 1: Chunk documents
all_chunks = []
for doc in docs:
    chunks = chunk_text(doc)
    all_chunks.extend(chunks)

print(f"\nTotal chunks created: {len(all_chunks)}")

# 🔥 Step 2: Embed chunks
embeddings = [get_embedding(chunk) for chunk in all_chunks]

# 🔥 Step 3: Store chunks
vector_store = VectorStore(dim=len(embeddings[0]))
vector_store.add(embeddings, all_chunks)

# Query
query = "What is RAG?"
query_embedding = get_embedding(query)

# 🔥 Step 4: Retrieve relevant chunks
results = vector_store.search(query_embedding, k=4)

print("\n🔍 RETRIEVED CHUNKS:\n")
for i, r in enumerate(results):
    print(f"{i+1}. {r[:200]}\n")

# 🔥 Step 5: Build structured prompt
prompt = build_prompt(results, query)

print("\n🧠 PROMPT SENT TO LLM:\n")
print(prompt[:500])  # print first part only


