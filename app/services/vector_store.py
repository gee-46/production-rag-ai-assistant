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
