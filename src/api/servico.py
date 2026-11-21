from dataclasses import dataclass

from src.api.catalogo import SelecaoModelo


@dataclass
class ResultadoAgente:
    """O que o agente devolve para a API."""
    resposta: str
    tokens_entrada: int | None = None
    tokens_saida: int | None = None
    origem_uso: str | None = None
    chamadas_modelo_observadas: int | None = None


@dataclass
class ResultadoConversa:
    """O que a API devolve ao final de uma conversa."""
    resposta: str
    memorias_usadas: list[str]
    tokens_entrada: int | None
    tokens_saida: int | None
    origem_uso: str | None = None
    chamadas_modelo_observadas: int | None = None


class Conversador:
    """Orquestra uma conversa: busca memórias e chama o agente."""

    def __init__(self, agente, memoria, k: int = 5, gerenciador=None):
        self.agente = agente
        self.memoria = memoria
        self.k = k
        self.gerenciador = gerenciador

    def conversar(self, usuario_id: str, mensagem: str,
              selecao: SelecaoModelo) -> ResultadoConversa:
        houve_esquecimento = False
        if self.gerenciador is not None:
            resultados = self.gerenciador.processar(usuario_id, mensagem)

            houve_esquecimento = any(
                resultado.efeito in {"esquecido", "usuario_apagado"}
                for resultado in resultados
            )

            if houve_esquecimento:
                self.agente.nova_sessao(usuario_id)

            confirmar = getattr(self.agente, 'registrar_operacao', None)
            if callable(confirmar):
                local = confirmar(usuario_id, mensagem, resultados, selecao)
                if local is not None:
                    return ResultadoConversa(
                        resposta=local.resposta, memorias_usadas=[], tokens_entrada=local.tokens_entrada,
                        tokens_saida=local.tokens_saida, origem_uso=local.origem_uso,
                        chamadas_modelo_observadas=local.chamadas_modelo_observadas)

        memorias = self.memoria.buscar(usuario_id, mensagem, self.k)
        r = self.agente.responder(usuario_id, mensagem, memorias, selecao)
        if houve_esquecimento and callable(getattr(self.agente, 'registrar_operacao', None)):
            self.agente.nova_sessao(usuario_id)
        return ResultadoConversa(
            resposta=r.resposta,
            memorias_usadas=[m["texto"] for m in memorias],
            tokens_entrada=r.tokens_entrada,
            tokens_saida=r.tokens_saida,
            origem_uso=getattr(r, "origem_uso", None),
            chamadas_modelo_observadas=getattr(r, "chamadas_modelo_observadas", None),
        )

    def nova_sessao(self, usuario_id: str) -> None:
        self.agente.nova_sessao(usuario_id)

    def esquecer_usuario(self, usuario_id: str) -> int:
        self.agente.nova_sessao(usuario_id)

        if self.gerenciador is not None:
            return self.gerenciador.limpar_usuario(usuario_id)

        return self.memoria.esquecer_usuario(usuario_id)
