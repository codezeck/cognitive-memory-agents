
from src.modelos.ollama_adapter import (
    OllamaAdapter,
    ModeloIndisponivelError,
    RespostaModeloVaziaError,
)

MODEL = "qwen2.5-coder:3b"

modelo_ia = OllamaAdapter(MODEL)

SYSTEM_PROMPT = """
Você é um agente de IA de um projeto acadêmico sobre memória
de longo prazo para agentes inteligentes.

Regras:
- Responda em português.
- Seja claro e objetivo.
- Utilize o histórico da conversa para manter o contexto.
- Utilize as memórias fornecidas quando forem relevantes.
- Considere informações mais recentes como possíveis atualizações.
- Não invente informações pessoais ou fatos não fornecidos.
- Se não houver informação suficiente, diga que não sabe.
- Diferencie informações confirmadas de suposições.
- Não misture informações de usuários diferentes.
"""

# Cada usuário terá seu próprio histórico.
historicos_por_usuario: dict[str, list[dict[str, str]]] = {}


def obter_historico(usuario_id: str) -> list[dict[str, str]]:
    """Retorna o histórico exclusivo do usuário informado."""

    usuario_id = usuario_id.strip()

    if not usuario_id:
        raise ValueError("O identificador do usuário é obrigatório.")

    if usuario_id not in historicos_por_usuario:
        historicos_por_usuario[usuario_id] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    return historicos_por_usuario[usuario_id]


def formatar_memorias(memorias: list | None) -> str:
    """Converte as memórias externas em contexto para o agente."""

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
        "As informações abaixo vieram da memória externa "
        "associada a este usuário. Use-as somente quando forem "
        "relevantes. Não misture essas informações com dados "
        "de outros usuários.\n"
        + "\n".join(textos)
    )


def responder(
    mensagem: str,
    usuario_id: str,
    memorias: list | None = None,
) -> str:
    """
    Responde usando o histórico do usuário e as memórias
    externas fornecidas para esse mesmo usuário.
    """

    if not isinstance(usuario_id, str) or not usuario_id.strip():
        raise ValueError("É necessário informar um usuario_id válido.")

    mensagem = mensagem.strip()

    if not mensagem:
        return ""

    historico = obter_historico(usuario_id)
    contexto_memoria = formatar_memorias(memorias)

    mensagens = [historico[0]]

    if contexto_memoria:
        mensagens.append({
            "role": "system",
            "content": f"Contexto de memória:\n{contexto_memoria}",
        })

    mensagens.extend(historico[1:])
    mensagens.append({"role": "user", "content": mensagem})

    try:
        texto = modelo_ia.gerar(mensagens)

    except Exception:
        # O histórico permanece inalterado se o Ollama falhar.
        raise

    historico.extend([
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": texto},
    ])

    return texto


def limpar_historico(usuario_id: str) -> None:
    """Limpa somente o histórico do usuário informado."""

    usuario_id = usuario_id.strip()

    if not usuario_id:
        raise ValueError("O identificador do usuário é obrigatório.")

    historicos_por_usuario[usuario_id] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]


def iniciar_agente() -> None:
    print(f"Agente iniciado com o modelo {MODEL}.")
    print("Modo de teste local: usuário demo.")
    print("Digite /sair para encerrar.\n")

    # Identificador fixo apenas para testar no terminal.
    usuario_id = "usuario_demo"

    while True:
        try:
            mensagem = input("Você: ").strip()

            if mensagem.lower() == "/sair":
                print("Agente encerrado.")
                break

            if not mensagem:
                continue

            resposta = responder(
                mensagem=mensagem,
                usuario_id=usuario_id,
            )

            print(f"\nAgente: {resposta}\n")

        except KeyboardInterrupt:
            print("\nAgente encerrado.")
            break

        except ModeloIndisponivelError:
            print(
                "\nNão foi possível conectar ao modelo de IA. "
                "Verifique se o Ollama está ativo e se o modelo "
                f"'{MODEL}' está instalado.\n"
            )

        except RespostaModeloVaziaError:
            print(
                "\nO modelo de IA não retornou uma resposta válida. "
                "Tente novamente.\n"
            )

        except Exception as erro:
            print(
                "\nOcorreu um erro inesperado. "
                "Tente novamente. "
                f"Detalhes técnicos: {erro}\n"
            )


if __name__ == "__main__":
    iniciar_agente()
