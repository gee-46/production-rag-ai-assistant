# -----------------------------
# Create / Load Vector Store
# -----------------------------

vector_store = VectorStore(dim=len(embeddings[0]))

loaded = vector_store.load()

if not loaded:

