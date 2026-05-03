def build_prompt(context_chunks, query):
    context = "\n\n".join(context_chunks)

    prompt = f"""
You are an AI assistant.

Answer the question using ONLY the provided context.

Rules:
- Do NOT use external knowledge
- Only answer if relevant information exists
- Respond ONLY in bullet points
- Do NOT add any introductory or concluding text
- Do NOT say phrases like "Here is the answer"
- Each bullet must be short and clear
- Maximum 4 bullets
- Do not combine too many ideas in one bullet

