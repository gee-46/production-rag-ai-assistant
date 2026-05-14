import faiss
import numpy as np
import pickle
import os


class VectorStore:

    def __init__(self, dim):

        self.index = faiss.IndexFlatL2(dim)

        self.texts = []


    # -----------------------------
    # Add embeddings
    # -----------------------------

    def add(self, embeddings, texts):

        embeddings = np.array(embeddings).astype("float32")

        self.index.add(embeddings)

        self.texts.extend(texts)


    # -----------------------------
    # Search similar chunks
    # -----------------------------

    def search(self, query_embedding, k=4):

        query_embedding = np.array([query_embedding]).astype("float32")

        distances, indices = self.index.search(query_embedding, k)

        results = []

        for idx in indices[0]:

            if idx < len(self.texts):

                results.append(self.texts[idx])

        return results


    # -----------------------------
    # Save FAISS index
    # -----------------------------

    def save(self):

        os.makedirs("storage", exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, "storage/faiss_index.bin")

        # Save chunk texts
        with open("storage/texts.pkl", "wb") as f:

            pickle.dump(self.texts, f)

        print("Vector store saved.")


    # -----------------------------
    # Load FAISS index
    # -----------------------------

    def load(self):

        if os.path.exists("storage/faiss_index.bin"):

            self.index = faiss.read_index("storage/faiss_index.bin")

            with open("storage/texts.pkl", "rb") as f:

                self.texts = pickle.load(f)

            print("Vector store loaded from disk.")

            return True

        return False
