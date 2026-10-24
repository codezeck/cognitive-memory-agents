
import ollama

MODEL = "qwen2.5-coder:3b"

SYSTEM_PROMPT = """
Você é um agente de IA de um projeto acadêmico sobre memória
de longo prazo para agentes inteligentes.

Regras:
- Responda em português.
- Seja claro e objetivo.
- Utilize o histórico da conversa para manter o contexto.
- Utilize as memórias fornecidas quando forem relevantes.
- Em caso de conflito, considere a informação mais recente
  como possível atualização, sem inventar dados.
- Não invente informações que não foram fornecidas.
"""

historico = [{"role": "system", "content": SYSTEM_PROMPT}]


def formatar_memorias(memorias: list | None) -> str:
    """Converte as memórias recebidas em contexto para o agente."""
    if not memorias:
        return ""

    textos = []

    for memoria in memorias:
        if isinstance(memoria, str):
            texto = memoria.strip()
        elif isinstance(memoria, dict):
            texto = str(
                memoria.get("texto")
                or memoria.get("content")
                or ""
            ).strip()
        else:
            continue

        if texto:
            textos.append(f"- {texto}")

    if not textos:
        return ""

    return (
        "As informações abaixo foram recuperadas de uma fonte "
        "de memória externa. Use-as somente quando forem relevantes. "
        "Se houver conflito ou dúvida, não invente uma resolução.\n"
        + "\n".join(textos)
    )


def responder(mensagem: str, memorias: list | None = None) -> str:
    """
    Responde usando o histórico atual e, opcionalmente,
    memórias fornecidas por um componente externo.
    """
    mensagem = mensagem.strip()

    if not mensagem:
        return ""

    contexto_memoria = formatar_memorias(memorias)

    # Mantém a memória externa separada do histórico permanente.
    mensagens = [historico[0]]

    if contexto_memoria:
        mensagens.append({
            "role": "system",
            "content": f"Contexto de memória:\n{contexto_memoria}",
        })

    mensagens.extend(historico[1:])
    mensagens.append({"role": "user", "content": mensagem})

    # Registra a mensagem no histórico da conversa.
    historico.append({"role": "user", "content": mensagem})

    try:
        resposta = ollama.chat(
            model=MODEL,
            messages=mensagens,
        )

        texto = resposta.message.content or ""
        historico.append({"role": "assistant", "content": texto})
        return texto

    except Exception:
        # Evita deixar uma mensagem sem resposta no histórico.
        historico.pop()
        raise


def iniciar_agente() -> None:
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
