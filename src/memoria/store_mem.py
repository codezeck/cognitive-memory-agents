"""Implementação em RAM da memória de longo prazo (testes e CI)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.memoria.embeddings import Embedder, EmbedderHash


@dataclass
class _Registro:
    id: str
    texto: str
    vetor: list[float]
    chave: str | None
    metadados: dict
    criado_em: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    substituida_por: str | None = None

    @property
    def ativa(self) -> bool:
        return self.substituida_por is None


def _validar_usuario(usuario_id: str) -> str:
    if not isinstance(usuario_id, str) or not usuario_id.strip():
        raise ValueError("É necessário informar um usuario_id válido.")
    return usuario_id.strip()


class MemoriaEmRam:
    def __init__(self, embedder: Embedder | None = None) -> None:
        self.embedder = embedder or EmbedderHash()
        self._dados: dict[str, list[_Registro]] = {}

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

        novo = _Registro(
            id=uuid.uuid4().hex,
            texto=texto,
            vetor=self.embedder.embed([texto])[0],
            chave=chave,
            metadados=dict(metadados or {}),
        )
        registros = self._dados.setdefault(usuario_id, [])
        if chave is not None:
            for r in registros:
                if r.chave == chave and r.ativa:
                    r.substituida_por = novo.id
        registros.append(novo)
        return novo.id

    def buscar(self, usuario_id: str, consulta: str, k: int = 5) -> list[dict]:
        usuario_id = _validar_usuario(usuario_id)
        ativas = [r for r in self._dados.get(usuario_id, []) if r.ativa]
        if not ativas or not consulta.strip() or k <= 0:
            return []

        q = self.embedder.embed([consulta])[0]
        pontuadas = [
            (sum(a * b for a, b in zip(q, r.vetor)), r) for r in ativas
        ]
        pontuadas = [(s, r) for s, r in pontuadas if s > 0]
        pontuadas.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": r.id, "texto": r.texto, "score": round(s, 4)}
            for s, r in pontuadas[:k]
        ]


    def listar_por_usuario(self, usuario_id: str) -> list[dict]:
        usuario_id = _validar_usuario(usuario_id)

        return [
            {
                "id": registro.id,
                "texto": registro.texto,
                "chave": registro.chave,
                "metadados": dict(registro.metadados),
                "ativa": registro.ativa,
            }
            for registro in self._dados.get(usuario_id, [])
        ]

    def atualizar(self, usuario_id: str, memoria_id: str, novo_texto: str) -> bool:
        usuario_id = _validar_usuario(usuario_id)
        novo_texto = novo_texto.strip()
        if not novo_texto:
            raise ValueError("O texto da memória não pode ser vazio.")
        for r in self._dados.get(usuario_id, []):
            if r.id == memoria_id and r.ativa:
                r.texto = novo_texto
                r.vetor = self.embedder.embed([novo_texto])[0]
                return True
        return False

    def esquecer(self, usuario_id: str, memoria_id: str) -> bool:
        usuario_id = _validar_usuario(usuario_id)
        registros = self._dados.get(usuario_id, [])
        for i, r in enumerate(registros):
            if r.id == memoria_id:
                del registros[i]
                return True
        return False

    def esquecer_usuario(self, usuario_id: str) -> int:
        usuario_id = _validar_usuario(usuario_id)
        return len(self._dados.pop(usuario_id, []))