@app.post("/query")
def query_rag(request: QueryRequest):

    query_embedding = get_embedding(request.query)

    results = vector_store.search(query_embedding, k=4)

    prompt = build_prompt(results, request.query)

    answer = generate_answer(prompt)

    return {
        "query": request.query,
        "answer": answer,
        "retrieved_chunks":  results
    }