from sentence_transformers import CrossEncoder

# Load reranker model
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank(query, chunks, top_k=3):

    # Create query-chunk pairs
    pairs = [[query, chunk] for chunk in chunks]

    # Predict relevance scores
    scores = reranker.predict(pairs)

    # Combine chunks with scores
    scored_chunks = list(zip(chunks, scores))

    # Sort by score descending
    scored_chunks.sort(
        key=lambda x: x[1],
        reverse=True
    )

    # Return top reranked chunks
    reranked_chunks = [
        chunk for chunk, score in scored_chunks[:top_k]
    ]

    return reranked_chunks