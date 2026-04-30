import ollama

def generate_answer(context, query):
    prompt = f"""
    You are an AI assistant. Answer ONLY using the given context.

    Context:
    {context}

    Question:
    {query}

    Answer:
    """

    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}]
    )

    return response['message']['content']