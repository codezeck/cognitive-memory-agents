"""Embeddings plugáveis, sem depender de Ollama."""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from typing import Protocol


class Embedder(Protocol):
    dimensao: int

    def embed(self, textos: list[str]) -> list[list[float]]:
        """Devolve um vetor normalizado (norma 1) por texto."""


def _tokens(texto: str) -> list[str]:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.findall(r"\w+", sem_acento)


class EmbedderHash:
    """Embedder determinístico por palavras (hashing trick).

    Mede sobreposição de palavras, não significado. Serve para testes e CI
    sem baixar modelo; a avaliação final deve usar um embedder semântico.
    """

    def __init__(self, dimensao: int = 256) -> None:
        self.dimensao = dimensao

    def embed(self, textos: list[str]) -> list[list[float]]:
        return [self._vetor(t) for t in textos]

    def _vetor(self, texto: str) -> list[float]:
        vetor = [0.0] * self.dimensao
        for token in _tokens(texto):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            vetor[h % self.dimensao] += 1.0
        norma = math.sqrt(sum(v * v for v in vetor))
        if norma == 0:
            return vetor
        return [v / norma for v in vetor]