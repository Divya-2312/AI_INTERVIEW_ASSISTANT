import ollama

response = ollama.chat(
    model="llama3.2:latest",
    messages=[
        {
            "role": "user",
            "content": "Generate one DBMS interview question only."
        }
    ]
)

print(response["message"]["content"])