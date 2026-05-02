def build_prompt(context_chunks, query):
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are an AI assistant that answers questions ONLY using the provided context.

Rules:
- Do not use external knowledge
- If answer is not in context, say "I don't know based on the provided information."

Context:
{context}

Question:
{query}

Answer:
"""

    return prompt