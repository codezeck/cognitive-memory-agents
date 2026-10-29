"""MemoriaSQLite (src/armazenamento) com `listar` e `esquecer_por_chave`.

Ver src/memoria/chaves.py. Não altera o repositório dos colegas: só estende
a classe e usa a mesma conexão, o mesmo bloqueio e a mesma tabela.
"""

from __future__ import annotations

import json

from src.armazenamento.repositorio import MemoriaSQLite, _validar_usuario


class MemoriaSQLiteComChaves(MemoriaSQLite):
    def listar(self, usuario_id: str) -> list[dict]:
        usuario_id = _validar_usuario(usuario_id)
        with self._lock:
            registros = self._con.execute(
                "SELECT id, texto, chave, metadados FROM memorias "
                "WHERE usuario_id = ? AND ativa = 1 ORDER BY criada_em",
                (usuario_id,),
            ).fetchall()
        return [
            {
                "id": r["id"],
                "texto": r["texto"],
                "chave": r["chave"],
                "metadados": json.loads(r["metadados"] or "{}"),
            }
            for r in registros
        ]

    def esquecer_por_chave(self, usuario_id: str, chave: str) -> int:
        usuario_id = _validar_usuario(usuario_id)
        with self._lock:
            if chave.endswith(":"):  # prefixo, ex.: "pet:gato:"
                cursor = self._con.execute(
                    "DELETE FROM memorias WHERE usuario_id = ? AND chave IS NOT NULL "
                    "AND substr(chave, 1, ?) = ?",
                    (usuario_id, len(chave), chave),
                )
            else:
                cursor = self._con.execute(
                    "DELETE FROM memorias WHERE usuario_id = ? AND chave = ?",
                    (usuario_id, chave),
                )
            self._con.commit()
        return cursor.rowcount
