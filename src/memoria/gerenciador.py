"""Aplica as decisões das regras sobre uma memória de longo prazo.

Política de conflitos:
- fato novo com a mesma chave e valor diferente substitui o antigo;
- fato repetido (mesma chave e mesmo valor) não duplica;
- "não moro mais em X" só apaga se o valor atual for X (evita apagar um
  fato mais novo);
- esquecer apaga também o histórico substituído daquela chave;
- apagar o usuário remove tudo.

Limitação: o índice chave -> ids fica em RAM, dentro deste objeto. Com uma
memória persistente seria preciso listar as memórias do usuário por chave
(ver docs/falhas-conhecidas-regras.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.memoria.base import MemoriaLongoPrazo
from src.memoria.regras import (
    APAGAR_USUARIO, ESQUECER, SALVAR, Decisao, extrair, normalizar,
)


@dataclass(frozen=True)
class Resultado:
    decisao: Decisao
    efeito: str  # salvo | atualizado | duplicado | esquecido | inexistente |
    #               conflito_ignorado | usuario_apagado


class GerenciadorMemoria:
    def __init__(
        self,
        memoria: MemoriaLongoPrazo,
        extrator: Callable[[str], list[Decisao]] = extrair,
    ) -> None:
        self.memoria = memoria
        self._extrator = extrator
        # usuario -> chave -> {"ids": [...], "valor": str, "norm": str}
        self._indice: dict[str, dict[str, dict]] = {}

    @staticmethod
    def _usuario(usuario_id: str) -> str:
        if not isinstance(usuario_id, str) or not usuario_id.strip():
            raise ValueError("É necessário informar um usuario_id válido.")
        return usuario_id.strip()

    def processar(self, usuario_id: str, mensagem: str) -> list[Resultado]:
        uid = self._usuario(usuario_id)
        return [Resultado(d, self._aplicar(uid, d)) for d in self._extrator(mensagem)]

    def estado(self, usuario_id: str) -> dict[str, str]:
        uid = self._usuario(usuario_id)
        return {c: e["valor"] for c, e in self._indice.get(uid, {}).items()}

    def _aplicar(self, uid: str, d: Decisao) -> str:
        indice = self._indice.setdefault(uid, {})

        if d.acao == APAGAR_USUARIO:
            self.memoria.esquecer_usuario(uid)
            indice.clear()
            return "usuario_apagado"

        if d.acao == SALVAR:
            atual = indice.get(d.chave)
            if atual and atual["norm"] == normalizar(d.valor):
                return "duplicado"
            memoria_id = self.memoria.salvar(
                uid, d.texto, chave=d.chave, metadados={"origem": "regras", "valor": d.valor}
            )
            ids = (atual["ids"] if atual else []) + [memoria_id]
            indice[d.chave] = {"ids": ids, "valor": d.valor, "norm": normalizar(d.valor)}
            return "atualizado" if atual else "salvo"

        if d.acao == ESQUECER:
            if d.chave.endswith(":"):
                alvos = [c for c in indice if c.startswith(d.chave)]
            else:
                alvos = [d.chave] if d.chave in indice else []
            if not alvos:
                return "inexistente"
            if d.negacao and indice[alvos[0]]["norm"] != normalizar(d.valor or ""):
                return "conflito_ignorado"
            for chave in alvos:
                for memoria_id in indice.pop(chave)["ids"]:
                    self.memoria.esquecer(uid, memoria_id)
            return "esquecido"

        return "inexistente"
