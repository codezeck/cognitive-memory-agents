
import ollama

MODEL = "qwen2.5-coder:3b"

SYSTEM_PROMPT = """
Você é um agente de IA de um projeto acadêmico sobre memória
de longo prazo para agentes inteligentes.
Responda em português, com clareza e objetividade.
Use as mensagens anteriores para manter o contexto da conversa.
"""

historico = [
    {"role": "system", "content": SYSTEM_PROMPT}
]


def responder(mensagem: str) -> str:
    historico.append({"role": "user", "content": mensagem})

    resposta = ollama.chat(
        model=MODEL,
        messages=historico,
    )

    texto = resposta.message.content or ""

    historico.append({
        "role": "assistant",
        "content": texto,
    })

    return texto


if __name__ == "__main__":
    print("Agente iniciado. Digite /sair para encerrar.\n")

    while True:
        pergunta = input("Você: ").strip()

        if pergunta.lower() == "/sair":
            print("Agente encerrado.")
            break

        if not pergunta:
            continue

        try:
            print(f"\nAgente: {responder(pergunta)}\n")
        except ollama.ResponseError as erro:
            print(f"Erro do Ollama: {erro}")
            historico.pop()
        except Exception as erro:
            print(f"Falha ao consultar o modelo: {erro}")
            historico.pop()
