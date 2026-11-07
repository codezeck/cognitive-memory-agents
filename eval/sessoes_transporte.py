"""Transportes P6. Nenhuma mensagem de esquecimento é gerada implicitamente."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

import httpx

from eval.historico_processo import executar_historico_em_processo


@dataclass(frozen=True)
class Evento:
    id: str
    usuario_id: str
    sessao: int
    tipo: str
    texto: str | None = None
    chaves: tuple[str, ...] = ()


class Transporte(Protocol):
    cenario: str
    simulado: bool

    def validar(self, eventos: tuple[Evento, ...]) -> None: ...
    def executar(self, evento: Evento, *, provedor: str, modelo: str) -> dict: ...
    def fechar(self) -> None: ...


def mensagem_aprovada(evento: Evento, contratos: dict) -> str:
    if evento.tipo in {"fato", "pergunta"}:
        return evento.texto
    if not isinstance(contratos, dict):
        raise ValueError("Contratos de ações devem ser um objeto por identificador de evento.")
    contrato = contratos.get(evento.id, {})
    if (not isinstance(contrato, dict) or contrato.get("aprovado") is not True
            or not isinstance(contrato.get("referencia"), str) or not contrato["referencia"].strip()
            or not isinstance(contrato.get("mensagem"), str) or not contrato["mensagem"].strip()):
        raise ValueError(
            f"{evento.id}: esquecer_chaves exige mensagem e referência de aprovação externas; "
            "a API não possui exclusão por chave. Nenhuma mensagem será inventada."
        )
    return contrato["mensagem"]


@dataclass(frozen=True)
class Credencial:
    usuario_id: str
    token: str = field(repr=False)


class TransporteHTTP:
    cenario = "memoria_automatica"
    simulado = False

    def __init__(self, cliente: httpx.Client, credenciais: dict[str, Credencial], *,
                 contratos: dict | None = None, verificar_checkpoint: Callable | None = None):
        self.cliente = cliente
        self.credenciais = credenciais
        self.contratos = contratos or {}
        self.verificar_checkpoint = verificar_checkpoint

    def validar(self, eventos):
        usuarios = {e.usuario_id for e in eventos}
        if usuarios != self.credenciais.keys():
            raise ValueError("É necessário mapear exatamente os quatro usuários para credenciais dedicadas.")
        destinos = []
        for credencial in self.credenciais.values():
            if (not isinstance(credencial.usuario_id, str)
                    or not credencial.usuario_id.startswith("p6_")
                    or not 1 <= len(credencial.usuario_id) <= 64
                    or not all(c.isascii() and (c.isalnum() or c in "_.-") for c in credencial.usuario_id)
                    or not isinstance(credencial.token, str) or not credencial.token.strip()):
                raise ValueError("Use IDs dedicados com prefixo p6_ e tokens não vazios, provisionados na API.")
            destinos.append(credencial.usuario_id)
        if len(set(destinos)) != len(destinos):
            raise ValueError("Usuários diferentes não podem compartilhar a mesma identidade na API.")
        for evento in eventos:
            if evento.tipo == "esquecer_chaves":
                mensagem_aprovada(evento, self.contratos)

    def _pedido(self, evento, metodo, caminho, **kwargs):
        credencial = self.credenciais[evento.usuario_id]
        resposta = self.cliente.request(
            metodo, caminho, headers={"Authorization": f"Bearer {credencial.token}"}, **kwargs,
        )
        resposta.raise_for_status()
        return resposta.json() if resposta.content else {}

    def executar(self, evento, *, provedor, modelo):
        uid = self.credenciais[evento.usuario_id].usuario_id
        base = f"/usuarios/{uid}"
        if evento.tipo in {"fato", "pergunta", "esquecer_chaves"}:
            return self._pedido(evento, "POST", "/conversas", json={
                "usuario_id": uid, "mensagem": mensagem_aprovada(evento, self.contratos),
                "provedor": provedor, "modelo": modelo,
            })
        if evento.tipo == "iniciar_sessao":
            if evento.sessao == 1 and self._pedido(evento, "GET", base + "/estado-regras"):
                raise ValueError("Usuário dedicado já possui estado; prepare um ambiente limpo antes da execução.")
            return self._pedido(evento, "POST", base + "/sessoes")
        if evento.tipo == "apagar_usuario":
            return self._pedido(evento, "DELETE", base + "/memorias")
        if evento.tipo.startswith("checkpoint_"):
            estado = self._pedido(evento, "GET", base + "/estado-regras")
            observacao = {"estado_regras": estado}
            if self.verificar_checkpoint is not None:
                observacao.update(self.verificar_checkpoint(evento))
            return observacao
        raise ValueError(f"Tipo de evento não suportado: {evento.tipo}")

    def fechar(self):
        self.cliente.close()


class TransporteHistorico:
    """P1/P2 por episódio: o lote retorna somente depois da execução no filho.

    Sessões preservam o prefixo completo. Apagar usuário inicia outro episódio.
    Em falha do lote, parcelas não recebidas permanecem desconhecidas.
    """

    cenario = "historico_completo"
    simulado = False

    def __init__(self, *, contratos: dict | None = None, timeout=None, executor=None):
        self.contratos = contratos or {}
        self.timeout = timeout
        self.executor = executor or executar_historico_em_processo
        self._posicoes = {}
        self._episodios = []
        self._resultados = {}

    def validar(self, eventos):
        if self.timeout is not None:
            import math
            if not math.isfinite(self.timeout) or self.timeout <= 0:
                raise ValueError("Timeout do histórico deve ser positivo e finito.")
        self._posicoes, self._episodios, self._resultados = {}, [], {}
        atuais = {}
        for evento in eventos:
            if evento.tipo == "apagar_usuario":
                atuais.pop(evento.usuario_id, None)
            if evento.tipo not in {"fato", "pergunta", "esquecer_chaves"}:
                continue
            texto = mensagem_aprovada(evento, self.contratos)
            if evento.usuario_id not in atuais:
                atuais[evento.usuario_id] = len(self._episodios)
                self._episodios.append([])
            episodio = atuais[evento.usuario_id]
            self._posicoes[evento.id] = (episodio, len(self._episodios[episodio]))
            self._episodios[episodio].append(texto)

    def executar(self, evento, *, provedor, modelo):
        if evento.id not in self._posicoes:
            return {"motivo": "historico_sem_armazenamento_persistente"}
        episodio, posicao = self._posicoes[evento.id]
        if episodio not in self._resultados:
            try:
                chamadas = self.executor(
                    {"mensagens": list(self._episodios[episodio])}, provedor, modelo,
                    timeout=self.timeout,
                )
                if not isinstance(chamadas, list) or len(chamadas) != len(self._episodios[episodio]):
                    raise ValueError("Histórico não retornou todas as chamadas do episódio.")
                self._resultados[episodio] = chamadas
            except Exception as erro:
                self._resultados[episodio] = erro
        resultado = self._resultados[episodio]
        if isinstance(resultado, Exception):
            raise RuntimeError("Falha no lote de histórico; consumo não recebido é desconhecido.") from resultado
        return {**resultado[posicao], "origem": "lote_spawn", "memorias_usadas": []}

    def fechar(self):
        self._resultados.clear()
        self._episodios.clear()
        self._posicoes.clear()
