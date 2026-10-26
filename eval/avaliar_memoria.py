"""Roda o benchmark de memória e salva os resultados.

Uso (na raiz do projeto):
    python eval/avaliar_memoria.py
    python eval/avaliar_memoria.py --embedder hash --k 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memoria import EmbedderHash, MemoriaEmRam  # noqa: E402
from src.memoria.benchmark import avaliar, carregar, formatar_resumo  # noqa: E402

from src.memoria.embeddings_semantico import EmbedderFastembed  # noqa: E402

# Novos embedders entram aqui, sem mexer no resto.
EMBEDDERS = {"hash": EmbedderHash, "semantico": EmbedderFastembed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia a memória de longo prazo.")
    parser.add_argument("--embedder", choices=sorted(EMBEDDERS), default="hash")
    parser.add_argument("--k", type=int, default=3, help="memórias recuperadas por pergunta")
    parser.add_argument("--saida", default=None, help="arquivo JSON de resultados")
    args = parser.parse_args()

    embedder = EMBEDDERS[args.embedder]
    resultado = avaliar(carregar(), lambda: MemoriaEmRam(embedder()), k=args.k)

    print(formatar_resumo(resultado, args.embedder))

    saida = Path(args.saida) if args.saida else (
        Path(__file__).resolve().parent / "memoria" / f"resultados_{args.embedder}.json"
    )
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()