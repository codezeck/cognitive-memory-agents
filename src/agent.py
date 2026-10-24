
import ollama


# Configurações do agente
MODEL = "qwen2.5-coder:3b"

SYSTEM_PROMPT = """
Você é um agente de IA de um projeto acadêmico sobre memória
de longo prazo para agentes inteligentes.

Regras:
- Responda em português.
- Seja claro e objetivo.
- Utilize o histórico da conversa para manter o contexto.
- Não invente informações que não foram fornecidas.
"""

# Histórico temporário: permanece apenas durante esta execução
historico = [
    {"role": "system", "content": SYSTEM_PROMPT}
]


def responder(mensagem: str) -> str:
    """Envia uma mensagem ao Ollama e retorna a resposta do agente."""

    mensagem = mensagem.strip()

    if not mensagem:
        return ""

    historico.append({
        "role": "user",
        "content": mensagem,
    })

    try:
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

    except Exception:
        # Evita manter uma mensagem sem resposta no histórico.
        historico.pop()
        raise


def iniciar_agente() -> None:
    """Executa o chat interativo no terminal."""

    print(f"Agente iniciado com o modelo {MODEL}.")
    print("Digite /sair para encerrar.\n")

    while True:
        try:
            mensagem = input("Zeck: ").strip()

            if mensagem.lower() == "/sair":
                print("Agente encerrado.")
                break

            if not mensagem:
                continue

            resposta = responder(mensagem)
            print(f"\nAgente: {resposta}\n")

        except KeyboardInterrupt:
            print("\nAgente encerrado.")
            break

        except Exception as erro:
            print(f"\nErro ao consultar o Ollama: {erro}\n")


if __name__ == "__main__":
    iniciar_agente()
