from dataclasses import dataclass

from src.api.catalogo import SelecaoModelo


@dataclass
class ResultadoAgente:
    """O que o agente devolve para a API."""
    resposta: str
    tokens_entrada: int | None = None
    tokens_saida: int | None = None


@dataclass
class ResultadoConversa:
    """O que a API devolve ao final de uma conversa."""
    resposta: str
    memorias_usadas: list[str]
    tokens_entrada: int | None
    tokens_saida: int | None


class Conversador:
    """Orquestra uma conversa: busca memórias e chama o agente."""

    def __init__(self, agente, memoria, k: int = 5, gerenciador=None):
        self.agente = agente
        self.memoria = memoria
        self.k = k
        self.gerenciador = gerenciador

    def conversar(self, usuario_id: str, mensagem: str,
              selecao: SelecaoModelo) -> ResultadoConversa:

        if self.gerenciador is not None:
            resultados = self.gerenciador.processar(usuario_id, mensagem)

            houve_esquecimento = any(
                resultado.efeito in {"esquecido", "usuario_apagado"}
                for resultado in resultados
            )

            if houve_esquecimento:
                self.agente.nova_sessao(usuario_id)

        memorias = self.memoria.buscar(usuario_id, mensagem, self.k)
        r = self.agente.responder(usuario_id, mensagem, memorias, selecao)
        return ResultadoConversa(
            resposta=r.resposta,
            memorias_usadas=[m["texto"] for m in memorias],
            tokens_entrada=r.tokens_entrada,
            tokens_saida=r.tokens_saida,
        )

    def nova_sessao(self, usuario_id: str) -> None:
        self.agente.nova_sessao(usuario_id)

    def esquecer_usuario(self, usuario_id: str) -> int:
        # limpa também a conversa guardada na RAM do agente (LGPD)
        self.agente.nova_sessao(usuario_id)
        return self.memoria.esquecer_usuario(usuario_id)