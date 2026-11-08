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
    def verificar_inicio(self, eventos, *, execucao_id, provedor, modelo) -> dict: ...
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
        self._pronto = False

    def identificar(self):
        return {"api_url": str(self.cliente.base_url),
                "usuarios": {u: c.usuario_id for u, c in self.credenciais.items()},
                "configuracao_efetiva_declarada": None}

    def verificar_inicio(self, eventos, *, execucao_id, provedor, modelo):
        """Só GETs autenticados; nenhuma resposta/fato antes da barreira global."""
        self._pronto = False
        falhas = []
        for uid, credencial in self.credenciais.items():
            evento = Evento(f"{uid}/s1/preflight", uid, 1, "preflight")
            try:
                estado = self._pedido(evento, "GET", f"/usuarios/{credencial.usuario_id}/estado-regras")
                if not isinstance(estado, dict) or estado:
                    raise ValueError("estado inicial incompatível")
            except Exception as erro:
                # Não copiar mensagens HTTP potencialmente contendo tokens.
                status = getattr(getattr(erro, "response", None), "status_code", None)
                falhas.append(f"{uid}: {type(erro).__name__}" + (f" HTTP {status}" if status is not None else ""))
        if falhas:
            raise ValueError("Preflight de autenticação/estado recusado: " + "; ".join(falhas))
        verificador = self.verificar_checkpoint
        if not all(callable(getattr(verificador, k, None)) for k in ("preparar", "proveniencia")):
            raise ValueError("P6 bloqueada: evidência inicial aprovada de banco e histórico limpos é obrigatória (Paloma).")
        verificador.preparar(
            execucao_id=execucao_id, api_url=str(self.cliente.base_url),
            usuarios={u: c.usuario_id for u, c in self.credenciais.items()},
            provedor=provedor, modelo=modelo,
        )
        evidencias = {}
        for uid in self.credenciais:
            evidencia = verificador(Evento(f"{uid}/s1/preflight", uid, 1, "preflight"))
            if (evidencia.get("evidencia_status") != "compativel"
                    or not all(type(evidencia.get(k)) is int and evidencia[k] == 0
                               for k in ("alvos_ativos", "alvos_substituidos", "alvos_no_historico"))):
                raise ValueError(f"{uid}: falta evidência inicial compatível de ativos, inativos e histórico vazios.")
            evidencias[uid] = evidencia
        catalogo = self._pedido(evento, "GET", "/provedores")
        selecionado = next((p for p in catalogo if isinstance(p, dict)
                            and p.get("provedor") == provedor and p.get("modelo") == modelo
                            and p.get("configurado") is True), None) if isinstance(catalogo, list) else None
        if selecionado is None:
            raise ValueError("Preflight recusado: modelo/provedor não permitido ou não configurado em GET /provedores.")
        self._pronto = True
        self._provedor, self._modelo = provedor, modelo
        return {**verificador.proveniencia(), "autenticados": list(self.credenciais),
                "evidencias_iniciais": evidencias,
                "catalogo_api_selecao": {k: selecionado.get(k) for k in ("provedor", "modelo", "local", "configurado", "padrao")}}

    def validar(self, eventos):
        if self.cliente.base_url.username or self.cliente.base_url.password or self.cliente.base_url.query or self.cliente.base_url.fragment:
            raise ValueError("Base URL deve identificar a API sem credenciais, consulta ou fragmento.")
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
        if not self._pronto:
            raise ValueError("Verificação operacional inicial obrigatória antes dos eventos HTTP.")
        if (provedor, modelo) != (self._provedor, self._modelo):
            raise ValueError("Seleção de provedor/modelo mudou após a verificação inicial.")
        uid = self.credenciais[evento.usuario_id].usuario_id
        base = f"/usuarios/{uid}"
        if evento.tipo in {"fato", "pergunta", "esquecer_chaves", "apagar_usuario"}:
            marcar = getattr(self.verificar_checkpoint, "marcar_acao", None)
            if marcar:
                marcar(evento)
        if evento.tipo in {"fato", "pergunta", "esquecer_chaves"}:
            resposta = self._pedido(evento, "POST", "/conversas", json={
                "usuario_id": uid, "mensagem": mensagem_aprovada(evento, self.contratos),
                "provedor": provedor, "modelo": modelo,
            })
            resposta["configuracao_compativel"] = None if any(
                resposta.get(k) is None for k in ("provedor", "modelo")) else not any(
                resposta.get(k) is not None and resposta[k] != esperado
                for k, esperado in (("provedor", provedor), ("modelo", modelo)))
            return resposta
        if evento.tipo == "iniciar_sessao":
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
        self._pronto = False
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

    def verificar_inicio(self, eventos, *, execucao_id, provedor, modelo):
        return {"isolamento": "processos_spawn_por_episodio", "memorias": [],
                "provedor_solicitado": provedor, "modelo_solicitado": modelo}

    def fechar(self):
        self._resultados.clear()
        self._episodios.clear()
        self._posicoes.clear()
