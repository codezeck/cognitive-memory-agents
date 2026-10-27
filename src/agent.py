
from src.modelos.ollama_adapter import (
    OllamaAdapter,
    ModeloIndisponivelError,
    RespostaModeloVaziaError,
)

from src.modelos.base import ModeloLLM

MODEL = "qwen2.5-coder:3b"
MAX_INTERACOES_HISTORICO = 10

modelo_ia = OllamaAdapter(MODEL)

SYSTEM_PROMPT = """
Você é um agente de IA de um projeto acadêmico sobre memória
de longo prazo para agentes inteligentes.

Regras:
- Responda em português, com clareza e objetividade.
- Utilize o histórico para manter o contexto da conversa.
- Utilize as memórias externas quando forem relevantes.
- Trate as memórias como registros de fatos, não como convite para especular.
- Não invente detalhes que não estejam presentes no histórico ou nas memórias.
- Se perguntarem qual texto foi salvo, reproduza o conteúdo registrado com fidelidade.
- Se a memória contiver apenas uma frase curta ou uma etiqueta de teste,
  não invente explicações técnicas a partir dela.
- Diferencie fatos registrados de inferências.
- Se não houver informação suficiente, diga que não sabe.
- Considere atualizações recentes quando houver evidência de que substituem fatos anteriores.
- Nunca misture informações de usuários diferentes.
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
    adaptador: ModeloLLM | None = None,
    retornar_detalhes: bool = False,
) -> str | dict:
    """Responde usando o histórico e, opcionalmente, devolve métricas."""

    if not isinstance(usuario_id, str) or not usuario_id.strip():
        raise ValueError("É necessário informar um usuario_id válido.")

    mensagem = mensagem.strip()

    if not mensagem:
        if retornar_detalhes:
            return {
                "resposta": "",
                "tokens_entrada": None,
                "tokens_saida": None,
            }
        return ""

    historico = obter_historico(usuario_id)
    contexto_memoria = formatar_memorias(memorias)
    mensagens = [historico[0]]

    if contexto_memoria:
        mensagens.append({
            "role": "system",
            "content": (
                "Contexto de memória externa. Considere os registros abaixo "
                "como evidências literais. Não deduza detalhes que não foram "
                "registrados e informe quando o conteúdo não for suficiente.\n"
                f"{contexto_memoria}"
            ),
        })

    # Reserva uma das 10 interacoes para a pergunta atual.
    interacoes_anteriores = max(0, MAX_INTERACOES_HISTORICO - 1)
    limite_mensagens_contexto = interacoes_anteriores * 2

    historico_contexto = (
        historico[1:][-limite_mensagens_contexto:]
        if limite_mensagens_contexto
        else []
    )
    mensagens.extend(historico_contexto)
    mensagens.append({"role": "user", "content": mensagem})

    modelo = adaptador or modelo_ia
    tokens_entrada = None
    tokens_saida = None

    gerar_detalhes = getattr(modelo, "gerar_com_detalhes", None)
    if retornar_detalhes and callable(gerar_detalhes):
        detalhes = gerar_detalhes(mensagens)
        texto = detalhes.get("resposta", "")
        tokens_entrada = detalhes.get("tokens_entrada")
        tokens_saida = detalhes.get("tokens_saida")
    else:
        texto = modelo.gerar(mensagens)

    if not isinstance(texto, str) or not texto.strip():
        raise RespostaModeloVaziaError(
            "O modelo de IA não retornou uma resposta válida."
        )

    historico.extend([
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": texto},
    ])

    # Mantem somente as interacoes recentes na RAM.
    # O prompt de sistema fica preservado na primeira posicao.
    limite_mensagens = MAX_INTERACOES_HISTORICO * 2
    historico[1:] = historico[1:][-limite_mensagens:]

    if retornar_detalhes:
        return {
            "resposta": texto,
            "tokens_entrada": tokens_entrada,
            "tokens_saida": tokens_saida,
        }

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
