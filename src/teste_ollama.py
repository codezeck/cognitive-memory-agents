import ollama

r = ollama.chat(
    model="qwen2.5-coder:7b",
    messages=[{"role": "user", "content": "Diga olá em uma frase."}],
)
print(r["message"]["content"])
