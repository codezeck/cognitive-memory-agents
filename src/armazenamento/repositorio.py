
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone

from src.armazenamento.banco import conectar
from src.memoria.embeddings import Embedder, EmbedderHash


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validar_usuario(usuario_id: str) -> str:
    if not isinstance(usuario_id, str) or not usuario_id.strip():
        raise ValueError("É necessário informar um usuario_id válido.")
    return usuario_id.strip()


class MemoriaSQLite:
    def __init__(
        self,
        caminho: str | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.embedder = embedder or EmbedderHash()
        self._con = conectar(caminho)
        self._lock = threading.RLock()

    def salvar(
        self,
        usuario_id: str,
        texto: str,
        chave: str | None = None,
        metadados: dict | None = None,
    ) -> str:
        usuario_id = _validar_usuario(usuario_id)
        texto = texto.strip()

        if not texto:
            raise ValueError("O texto da memória não pode ser vazio.")

        vetor = self.embedder.embed([texto])[0]
        memoria_id = uuid.uuid4().hex
        agora = _agora()

        with self._lock:
            try:
                self._con.execute("BEGIN")

                if chave is not None:
                    self._con.execute(
                        """
                        UPDATE memorias
                        SET ativa = 0, atualizada_em = ?
                        WHERE usuario_id = ? AND chave = ? AND ativa = 1
                        """,
                        (agora, usuario_id, chave),
                    )

                self._con.execute(
                    """
                    INSERT INTO memorias (
                        id, usuario_id, texto, ativa,
                        criada_em, atualizada_em, chave,
                        metadados, vetor
                    )
                    VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (
                        memoria_id,
                        usuario_id,
                        texto,
                        agora,
                        agora,
                        chave,
                        json.dumps(metadados or {}, ensure_ascii=False),
                        json.dumps(vetor),
                    ),
                )
                self._con.commit()
            except Exception:
                self._con.rollback()
                raise

        return memoria_id

    def buscar(
        self, usuario_id: str, consulta: str, k: int = 5
    ) -> list[dict]:
        usuario_id = _validar_usuario(usuario_id)

        if not isinstance(consulta, str):
            raise ValueError("A consulta deve ser um texto válido.")

        if not consulta.strip() or k <= 0:
            return []

        consulta_vetor = self.embedder.embed([consulta])[0]

        with self._lock:
            registros = self._con.execute(
                """
                SELECT id, texto, vetor
                FROM memorias
                WHERE usuario_id = ? AND ativa = 1
                """,
                (usuario_id,),
            ).fetchall()

        pontuadas = []

        for registro in registros:
            vetor = json.loads(registro["vetor"])

            # Um vetor vazio indica um registro anterior à migração.
            if not vetor:
                vetor = self.embedder.embed([registro["texto"]])[0]

            if len(vetor) != len(consulta_vetor):
                continue

            score = sum(
                a * b for a, b in zip(consulta_vetor, vetor)
            )

            if score > 0:
                pontuadas.append((score, registro))

        pontuadas.sort(key=lambda item: item[0], reverse=True)

        return [
            {
                "id": registro["id"],
                "texto": registro["texto"],
                "score": round(score, 4),
            }
            for score, registro in pontuadas[:k]
        ]


    def listar_por_usuario(self, usuario_id: str) -> list[dict]:
        usuario_id = _validar_usuario(usuario_id)

        with self._lock:
            registros = self._con.execute(
                """
                SELECT id, texto, chave, metadados, ativa
                FROM memorias
                WHERE usuario_id = ?
                ORDER BY criada_em ASC
                """,
                (usuario_id,),
            ).fetchall()

        return [
            {
                "id": registro["id"],
                "texto": registro["texto"],
                "chave": registro["chave"],
                "metadados": json.loads(
                    registro["metadados"] or "{}"
                ),
                "ativa": bool(registro["ativa"]),
            }
            for registro in registros
        ]


    def atualizar(
        self, usuario_id: str, memoria_id: str, novo_texto: str
    ) -> bool:
        usuario_id = _validar_usuario(usuario_id)
        novo_texto = novo_texto.strip()

        if not novo_texto:
            raise ValueError("O texto da memória não pode ser vazio.")

        vetor = self.embedder.embed([novo_texto])[0]

        with self._lock:
            cursor = self._con.execute(
                """
                UPDATE memorias
                SET texto = ?, vetor = ?, atualizada_em = ?
                WHERE id = ? AND usuario_id = ? AND ativa = 1
                """,
                (
                    novo_texto,
                    json.dumps(vetor),
                    _agora(),
                    memoria_id,
                    usuario_id,
                ),
            )
            self._con.commit()

        return cursor.rowcount > 0

    def esquecer(self, usuario_id: str, memoria_id: str) -> bool:
        usuario_id = _validar_usuario(usuario_id)

        with self._lock:
            cursor = self._con.execute(
                "DELETE FROM memorias WHERE id = ? AND usuario_id = ?",
                (memoria_id, usuario_id),
            )
            self._con.commit()

        return cursor.rowcount > 0

    def esquecer_usuario(self, usuario_id: str) -> int:
        usuario_id = _validar_usuario(usuario_id)

        with self._lock:
            cursor = self._con.execute(
                "DELETE FROM memorias WHERE usuario_id = ?",
                (usuario_id,),
            )
            quantidade = cursor.rowcount
            self._con.commit()

        return quantidade

    def fechar(self) -> None:
        with self._lock:
            self._con.close()
