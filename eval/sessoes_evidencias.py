"""Contrato LOCAL de evidências P6; não acrescenta endpoints nem opera o banco.

Declarações de aprovação são externas. O hash identifica o documento lido;
não autentica quem o produziu. Ausência bloqueia o início ou deixa checkpoint
não verificado. Documentos incompatíveis nunca são aproveitados parcialmente.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path


class TimeoutEvidencia(TimeoutError):
    """O prazo terminou sem evidência completa; a rodada deve parar."""


class EvidenciaIncompativel(ValueError):
    """Documento encontrado, mas rejeitado; não deve ser aguardado novamente."""


def validar_prazos(timeout, intervalo):
    for nome, valor in (("timeout de evidência", timeout), ("intervalo de evidência", intervalo)):
        if type(valor) not in (int, float) or not math.isfinite(valor) or valor <= 0:
            raise ValueError(f"{nome} deve ser positivo e finito.")


def campos_checkpoint(evento):
    if evento.tipo == "checkpoint_persistencia":
        return ("reinicio_confirmado", "estado_antes", "estado_depois")
    if evento.tipo == "checkpoint_exclusao":
        return ("alvos_antes", "alvos_ativos", "alvos_substituidos", "alvos_no_historico", "nao_alvos_preservados")
    raise ValueError("A espera é exclusiva de checkpoints de persistência ou exclusão.")


def medicao_completa(evento, resultado):
    """Completude é diferente de aprovação; zero na RAM nunca é inferido."""
    campos_checkpoint(evento)
    if resultado.get("evidencia_status") != "compativel":
        return False
    tipos = ({"reinicio_confirmado": lambda v: type(v) is bool,
              "estado_antes": lambda v: isinstance(v, (dict, list)),
              "estado_depois": lambda v: isinstance(v, (dict, list))}
             if evento.tipo == "checkpoint_persistencia" else
             {**{c: lambda v: type(v) is int and v >= 0 for c in
                 ("alvos_antes", "alvos_ativos", "alvos_substituidos", "alvos_no_historico")},
              "nao_alvos_preservados": lambda v: type(v) is bool})
    for campo, validar in tipos.items():
        valor = resultado.get(campo)
        if valor is not None and not validar(valor):
            raise EvidenciaIncompativel(f"{evento.id}: medição inválida em {campo}.")
    if evento.tipo == "checkpoint_persistencia":
        return (type(resultado.get("reinicio_confirmado")) is bool
                and isinstance(resultado.get("estado_antes"), (dict, list))
                and isinstance(resultado.get("estado_depois"), (dict, list)))
    return (all(type(resultado.get(c)) is int and resultado[c] >= 0 for c in
                ("alvos_ativos", "alvos_substituidos", "alvos_no_historico"))
            and type(resultado.get("alvos_antes")) is int and resultado["alvos_antes"] > 0
            and type(resultado.get("nao_alvos_preservados")) is bool)


class VerificadorEvidencias:
    def __init__(self, caminho):
        self.caminho = Path(caminho) if caminho else None

    def preparar(self, *, execucao_id, api_url, usuarios, provedor, modelo):
        self.execucao_id = execucao_id
        self.api_url = api_url.rstrip("/")
        self.usuarios = dict(usuarios)
        self.provedor, self.modelo = provedor, modelo
        self.iniciado_em = datetime.now(timezone.utc)
        self.limites = {}
        documento, _ = self._ler()
        if documento is None:
            raise ValueError("P6 bloqueada: Paloma deve fornecer evidência inicial aprovada em --evidencias.")
        configuracao = documento.get("configuracao_efetiva", {})
        if (not isinstance(configuracao, dict)
                or configuracao.get("agente_real") is not True
                or configuracao.get("provedor") != provedor
                or configuracao.get("modelo") != modelo
                or not self._texto(configuracao.get("backend_id"))
                or configuracao.get("backend_historico_id") != configuracao["backend_id"]
                or not self._texto(configuracao.get("commit_api"))):
            raise ValueError("Configuração efetiva externa ausente/incompatível: agente real, modelo, provedor e backend equivalente exigidos.")
        self.ambiente_id = documento["ambiente_id"]
        self.configuracao = configuracao

    @staticmethod
    def _texto(valor):
        return isinstance(valor, str) and bool(valor.strip())

    def _ler(self):
        if self.caminho is None or not self.caminho.exists():
            return None, None
        try:
            bruto = self.caminho.read_bytes()
        except FileNotFoundError:
            return None, None
        documento = json.loads(bruto)
        if (not isinstance(documento, dict)
                or documento.get("execucao_id") != self.execucao_id
                or not isinstance(documento.get("api_url"), str)
                or documento["api_url"].rstrip("/") != self.api_url
                or documento.get("usuarios") != self.usuarios
                or not self._texto(documento.get("ambiente_id"))
                or not isinstance(documento.get("eventos"), dict)):
            raise ValueError("Proveniência das evidências incompatível com execução, API ou usuários.")
        if hasattr(self, "ambiente_id") and (
                documento["ambiente_id"] != self.ambiente_id
                or documento.get("configuracao_efetiva") != self.configuracao):
            raise ValueError("Ambiente/configuração das evidências mudou durante a execução.")
        return documento, hashlib.sha256(bruto).hexdigest()

    def __call__(self, evento):
        documento, digest = self._ler()
        if documento is None or evento.id not in documento["eventos"]:
            return {"evidencia_status": "ausente"}
        entrada = documento["eventos"][evento.id]
        if not isinstance(entrada, dict):
            raise ValueError(f"{evento.id}: evidência deve ser objeto.")
        identidade = {
            "execucao_id": self.execucao_id, "ambiente_id": self.ambiente_id,
            "usuario_id": evento.usuario_id, "usuario_api_id": self.usuarios[evento.usuario_id],
            "sessao": evento.sessao, "evento_id": evento.id, "tipo": evento.tipo,
            "chaves": list(evento.chaves),
        }
        if (any(entrada.get(k) != v for k, v in identidade.items())
                or type(entrada.get("sessao")) is not int
                or entrada.get("aprovado") is not True
                or any(not self._texto(entrada.get(k)) for k in ("responsavel", "referencia", "origem"))
                or not isinstance(entrada.get("observacao"), dict)):
            raise ValueError(f"{evento.id}: identidade, escopo ou aprovação da evidência incompatível.")
        try:
            instante = datetime.fromisoformat(entrada["coletado_em"])
            if instante.tzinfo is None or instante > datetime.now(timezone.utc):
                raise ValueError()
            if evento.tipo.startswith("checkpoint_") and instante < self.limites.get(evento.usuario_id, self.iniciado_em):
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"{evento.id}: data da evidência inválida ou anterior à execução.") from None
        observacao = entrada["observacao"]
        if evento.tipo == "checkpoint_exclusao":
            if type(observacao.get("alvos_antes")) is not int or observacao["alvos_antes"] <= 0:
                raise ValueError(f"{evento.id}: exclusão exige evidência dos alvos antes da ação.")
        return {**observacao, "evidencia_status": "compativel",
                "evidencia": {**identidade, "documento_sha256": digest,
                              **{k: entrada[k] for k in ("responsavel", "referencia", "origem", "coletado_em")}}}

    def marcar_acao(self, evento):
        self.limites[evento.usuario_id] = datetime.now(timezone.utc)

    def aguardar(self, evento, *, timeout, intervalo):
        """Consulta somente o arquivo. O chamador registra a espera antes de entrar."""
        validar_prazos(timeout, intervalo)
        campos_checkpoint(evento)
        limite = time.monotonic() + timeout
        while True:
            if time.monotonic() >= limite:
                raise TimeoutEvidencia(f"{evento.id}: prazo de evidência esgotado ({timeout:g}s).")
            try:
                resultado = self(evento)
            except (ValueError, OSError) as erro:
                raise EvidenciaIncompativel(f"{evento.id}: evidência rejeitada: {erro}") from erro
            # A leitura também consome prazo: não aceitar documento recebido depois dele.
            restante = limite - time.monotonic()
            if restante <= 0:
                raise TimeoutEvidencia(f"{evento.id}: prazo de evidência esgotado ({timeout:g}s).")
            if medicao_completa(evento, resultado):
                return resultado
            time.sleep(min(intervalo, restante))

    def proveniencia(self):
        return {"api_url": self.api_url, "ambiente_id": self.ambiente_id,
                "usuarios": dict(self.usuarios), "configuracao_efetiva_declarada": {
                    k: self.configuracao[k] for k in ("agente_real", "provedor", "modelo", "backend_id",
                                                     "backend_historico_id", "commit_api")},
                "limite": "aprovação externa declarada; hash não autentica o produtor"}
