"""Aplica as decisões das regras sobre uma memória de longo prazo.

O gerenciador NÃO guarda estado: o valor atual de cada chave e o apagamento
por tópico vêm da própria memória (`listar` e `esquecer_por_chave`). Assim
ele continua correto quando outro caminho mexe na memória (API, outro
processo, reinício).

Política de conflitos:
- fato novo com a mesma chave e valor diferente substitui o antigo;
- fato repetido (mesma chave e mesmo valor) não duplica;
- "não moro mais em X" só apaga se o valor atual for X (evita apagar um
  fato mais novo);
- esquecer apaga também o histórico substituído daquela chave;
- apagar o usuário remove tudo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.memoria.chaves import MemoriaComChaves
from src.memoria.regras import (
    APAGAR_USUARIO, ESQUECER, SALVAR, Decisao, extrair, normalizar,
)


@dataclass(frozen=True)
class Resultado:
    decisao: Decisao
    efeito: str  # salvo | atualizado | duplicado | esquecido | inexistente |
    #               conflito_ignorado | usuario_apagado


def _valor(memoria: dict) -> str:
    """Valor guardado pelas regras; memórias criadas à mão usam o texto."""
    return (memoria.get("metadados") or {}).get("valor") or memoria["texto"]


class GerenciadorMemoria:
    def __init__(
        self,
        memoria: MemoriaComChaves,
        extrator: Callable[[str], list[Decisao]] = extrair,
    ) -> None:
        if not isinstance(memoria, MemoriaComChaves):
            raise TypeError(
                "GerenciadorMemoria precisa de uma memória com listar() e "
                "esquecer_por_chave() (ver src/memoria/chaves.py)."
            )
        self.memoria = memoria
        self._extrator = extrator

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
        return {m["chave"]: _valor(m) for m in self.memoria.listar(uid) if m["chave"]}

    def _ativas_por_chave(self, uid: str) -> dict[str, dict]:
        return {m["chave"]: m for m in self.memoria.listar(uid) if m["chave"]}

    def _aplicar(self, uid: str, d: Decisao) -> str:
        if d.acao == APAGAR_USUARIO:
            self.memoria.esquecer_usuario(uid)
            return "usuario_apagado"

        if d.acao == SALVAR:
            atual = self._ativas_por_chave(uid).get(d.chave)
            if atual and normalizar(_valor(atual)) == normalizar(d.valor):
                return "duplicado"
            self.memoria.salvar(
                uid, d.texto, chave=d.chave, metadados={"origem": "regras", "valor": d.valor}
            )
            return "atualizado" if atual else "salvo"

        if d.acao == ESQUECER:
            if d.negacao and not d.chave.endswith(":"):
                atual = self._ativas_por_chave(uid).get(d.chave)
                if atual and normalizar(_valor(atual)) != normalizar(d.valor or ""):
                    return "conflito_ignorado"
            apagadas = self.memoria.esquecer_por_chave(uid, d.chave)
            return "esquecido" if apagadas else "inexistente"

        return "inexistente"
