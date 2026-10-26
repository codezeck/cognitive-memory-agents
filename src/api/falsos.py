from src.api.servico import ResultadoAgente


class AgenteFalso:
    """Agente de mentira: serve para testar a API sem o Ollama."""

    def __init__(self, falhar_com: Exception | None = None):
        self.falhar_com = falhar_com   # se informado, o agente "quebra" com esse erro
        self.chamadas: list[dict] = []
        self.sessoes_novas: list[str] = []

    def responder(self, usuario_id: str, mensagem: str, memorias: list,
                  selecao) -> ResultadoAgente:
        self.chamadas.append({"usuario_id": usuario_id, "mensagem": mensagem,
                              "memorias": memorias, "selecao": selecao})
        if self.falhar_com:
            raise self.falhar_com
        return ResultadoAgente(resposta="Resposta de teste",
                               tokens_entrada=10, tokens_saida=5)

    def nova_sessao(self, usuario_id: str) -> None:
        self.sessoes_novas.append(usuario_id)