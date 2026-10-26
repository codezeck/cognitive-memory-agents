"""Embedder semântico local (fastembed + ONNX), sem Ollama e a custo zero.

O modelo é baixado do Hugging Face na primeira execução e fica em cache.
Instale com: pip install -r requirements-memoria.txt
"""

from __future__ import annotations

import math

MODELO_PADRAO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _normalizar(vetor: list[float]) -> list[float]:
    norma = math.sqrt(sum(v * v for v in vetor))
    return [v / norma for v in vetor] if norma else vetor


class EmbedderFastembed:
    """Vetores normalizados (norma 1), como o `MemoriaEmRam` espera."""

    def __init__(self, modelo: str = MODELO_PADRAO) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as erro:
            raise ImportError(
                "fastembed não está instalado. Rode: "
                "pip install -r requirements-memoria.txt"
            ) from erro

        self.modelo = modelo
        self._modelo = TextEmbedding(model_name=modelo)
        self.dimensao = len(next(iter(self._modelo.embed(["teste"]))))

    def embed(self, textos: list[str]) -> list[list[float]]:
        return [_normalizar(v.tolist()) for v in self._modelo.embed(list(textos))]