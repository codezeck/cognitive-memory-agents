"""Memória com acesso por chave, para o gerenciador de regras ficar sem estado.

Por que existe: o `GerenciadorMemoria` precisa saber qual é o valor atual de
cada chave (ex.: "cidade") e apagar um tópico inteiro, inclusive o histórico
já substituído. Guardar isso em RAM no gerenciador quebra quando outro
caminho mexe na memória (a API apaga o usuário, cria uma memória à mão,
o processo reinicia). Aqui as duas operações vêm da própria memória.

- `listar(usuario_id)`: memórias ATIVAS, com id, texto, chave e metadados.
- `esquecer_por_chave(usuario_id, chave)`: apaga as memórias com essa chave,
  ativas e já substituídas. Chave terminada em ":" vale como prefixo
  (ex.: "pet:gato:"). Devolve quantas foram apagadas.

`MemoriaEmRamComChaves` (aqui) e `MemoriaSQLiteComChaves` (sqlite_chaves.py)
só acrescentam esses métodos às memórias existentes, sem alterar os arquivos
delas. Quando o grupo aprovar, os métodos podem ser movidos para
`store_mem.py` e `src/armazenamento/repositorio.py`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.memoria.base import MemoriaLongoPrazo
from src.memoria.store_mem import MemoriaEmRam, _validar_usuario


@runtime_checkable
class MemoriaComChaves(MemoriaLongoPrazo, Protocol):
    def listar(self, usuario_id: str) -> list[dict]:
        """Memórias ativas: [{"id", "texto", "chave", "metadados"}]."""

    def esquecer_por_chave(self, usuario_id: str, chave: str) -> int:
        """Apaga ativas e substituídas dessa chave (prefixo se terminar em ':')."""


def _casa(chave_registro: str | None, chave: str) -> bool:
    if chave_registro is None:
        return False
    return chave_registro.startswith(chave) if chave.endswith(":") else chave_registro == chave


class MemoriaEmRamComChaves(MemoriaEmRam):
    def listar(self, usuario_id: str) -> list[dict]:
        uid = _validar_usuario(usuario_id)
        return [
            {"id": r.id, "texto": r.texto, "chave": r.chave, "metadados": dict(r.metadados)}
            for r in self._dados.get(uid, [])
            if r.ativa
        ]

    def esquecer_por_chave(self, usuario_id: str, chave: str) -> int:
        uid = _validar_usuario(usuario_id)
        registros = self._dados.get(uid)
        if not registros:
            return 0
        restantes = [r for r in registros if not _casa(r.chave, chave)]
        apagadas = len(registros) - len(restantes)
        self._dados[uid] = restantes
        return apagadas
