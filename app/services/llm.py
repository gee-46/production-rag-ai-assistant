import ollama

def generate_answer(prompt):
    response = ollama.chat(
        model="llama3",
        messages=[{"role": "user", "content": prompt}]
    )

    return response['message']['content']