"""Contrato LOCAL de evidências P6; não acrescenta endpoints nem opera o banco.

Declarações de aprovação são externas. O hash identifica o documento lido;
não autentica quem o produziu. Ausência bloqueia o início ou deixa checkpoint
não verificado. Documentos incompatíveis nunca são aproveitados parcialmente.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


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
        bruto = self.caminho.read_bytes()
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
        entrada = documento["eventos"].get(evento.id) if documento else None
        if entrada is None:
            return {"evidencia_status": "ausente"}
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

    def proveniencia(self):
        return {"api_url": self.api_url, "ambiente_id": self.ambiente_id,
                "usuarios": dict(self.usuarios), "configuracao_efetiva_declarada": {
                    k: self.configuracao[k] for k in ("agente_real", "provedor", "modelo", "backend_id",
                                                     "backend_historico_id", "commit_api")},
                "limite": "aprovação externa declarada; hash não autentica o produtor"}
