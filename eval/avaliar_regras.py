"""Avalia o baseline por regras.

Uso (na raiz do projeto):
    python eval/avaliar_regras.py                       # conjunto de desenvolvimento
    python eval/avaliar_regras.py --conjunto avaliacao  # conjunto de avaliação final
    python eval/avaliar_regras.py --conjunto ambos --mostrar-falhas

O conjunto de avaliação final NÃO deve ser usado para ajustar as regras.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.memoria.chaves import MemoriaEmRamComChaves  # noqa: E402
from src.memoria.avaliacao_regras import (  # noqa: E402
    avaliar_conversas, avaliar_frases, carregar, formatar,
)

ARQUIVOS = {
    "dev": ("casos_dev.json", "conversas_dev.json"),
    "avaliacao": ("casos_avaliacao.json", "conversas_avaliacao.json"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Avalia o baseline por regras.")
    parser.add_argument("--conjunto", choices=["dev", "avaliacao", "ambos"], default="dev")
    parser.add_argument("--mostrar-falhas", action="store_true")
    parser.add_argument("--saida", default=None, help="arquivo JSON de resultados")
    args = parser.parse_args()

    nomes = ["dev", "avaliacao"] if args.conjunto == "ambos" else [args.conjunto]
    resultados = {}
    for nome in nomes:
        arq_frases, arq_conversas = ARQUIVOS[nome]
        frases = avaliar_frases(carregar(arq_frases))
        conversas = avaliar_conversas(carregar(arq_conversas), MemoriaEmRamComChaves)
        resultados[nome] = {"frases": frases, "conversas": conversas}
        print(formatar(nome, frases, conversas, args.mostrar_falhas))
        print()

    saida = Path(args.saida) if args.saida else (
        Path(__file__).resolve().parent / "memoria" / "regras" / f"resultados_{args.conjunto}.json"
    )
    saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultados salvos em {saida}")


if __name__ == "__main__":
    main()
