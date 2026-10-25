"""Executa o benchmark sintético de memória (eval/memoria/sessoes.json).

Mede só a recuperação (o que `buscar` devolve), sem chamar nenhum modelo de
linguagem: é determinístico, gratuito e roda no CI. Os tokens são
estimados (1 token ~ 4 caracteres), servem para comparar, não para cobrar.
"""

from __future__ import annotations

import json
import math
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Callable

from src.memoria.base import MemoriaLongoPrazo

CAMINHO_PADRAO = Path(__file__).resolve().parents[2] / "eval" / "memoria" / "sessoes.json"


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def estimar_tokens(texto: str) -> int:
    return math.ceil(len(texto) / 4) if texto else 0


def carregar(caminho: Path | str | None = None) -> dict:
    with open(caminho or CAMINHO_PADRAO, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _taxa(parte: int, total: int) -> float | None:
    return round(parte / total, 4) if total else None


def avaliar(
    dados: dict,
    criar_memoria: Callable[[], MemoriaLongoPrazo],
    k: int = 3,
) -> dict:
    memoria = criar_memoria()
    detalhes: list[dict] = []

    for usuario in dados["usuarios"]:
        uid = usuario["usuario_id"]
        ids_por_chave: dict[str, str] = {}
        historico: list[str] = []  # tudo que o usuário disse desde o último apagar
        ultima = max(s["sessao"] for s in usuario["sessoes"])
        sessoes = {s["sessao"]: s for s in usuario["sessoes"]}

        for numero in range(1, ultima + 1):
            sessao = sessoes.get(numero, {"fatos": []})

            if sessao.get("apagar_usuario"):
                memoria.esquecer_usuario(uid)
                ids_por_chave.clear()
                historico.clear()

            for chave in sessao.get("esquecer_chaves", []):
                memoria_id = ids_por_chave.pop(chave, None)
                if memoria_id:
                    memoria.esquecer(uid, memoria_id)

            for fato in sessao.get("fatos", []):
                ids_por_chave[fato["chave"]] = memoria.salvar(
                    uid, fato["texto"], chave=fato["chave"]
                )
                historico.append(fato["texto"])

            for q in (p for p in usuario["perguntas"] if p["apos_sessao"] == numero):
                recuperadas = memoria.buscar(uid, q["pergunta"], k=k)
                contexto = "\n".join(m["texto"] for m in recuperadas)
                texto = normalizar(contexto)

                recuperou = all(normalizar(t) in texto for t in q["esperado"])
                vazou = any(normalizar(t) in texto for t in q["proibido"])
                detalhes.append({
                    "usuario_id": uid,
                    "apos_sessao": numero,
                    "pergunta": q["pergunta"],
                    "tipo": q["tipo"],
                    "tem_esperado": bool(q["esperado"]),
                    "recuperou_esperado": recuperou,
                    "devolveu_proibido": vazou,
                    "acertou": recuperou and not vazou,
                    "tokens_memoria": estimar_tokens(contexto),
                    "tokens_historico_completo": estimar_tokens("\n".join(historico)),
                })

    return {
        "resumo": _resumir(detalhes, k),
        "por_tipo": _por_tipo(detalhes),
        "detalhes": detalhes,
    }


def _resumir(detalhes: list[dict], k: int) -> dict:
    total = len(detalhes)
    com_esperado = [d for d in detalhes if d["tem_esperado"]]
    sem_esperado = [d for d in detalhes if not d["tem_esperado"]]
    tok_mem = sum(d["tokens_memoria"] for d in detalhes)
    tok_his = sum(d["tokens_historico_completo"] for d in detalhes)
    return {
        "k": k,
        "perguntas": total,
        "taxa_acerto": _taxa(sum(d["acertou"] for d in detalhes), total),
        "taxa_lembranca_correta": _taxa(
            sum(d["recuperou_esperado"] for d in com_esperado), len(com_esperado)
        ),
        "taxa_informacao_desatualizada": _taxa(
            sum(d["devolveu_proibido"] for d in detalhes), total
        ),
        "taxa_esquecimento_correto": _taxa(
            sum(not d["devolveu_proibido"] for d in sem_esperado), len(sem_esperado)
        ),
        "tokens_medios_memoria": round(tok_mem / total, 1) if total else 0,
        "tokens_medios_historico_completo": round(tok_his / total, 1) if total else 0,
        "reducao_tokens_percentual": round(100 * (1 - tok_mem / tok_his), 1) if tok_his else None,
    }


def _por_tipo(detalhes: list[dict]) -> dict:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for d in detalhes:
        grupos[d["tipo"]].append(d)
    return {
        tipo: {"perguntas": len(g), "acertos": sum(d["acertou"] for d in g)}
        for tipo, g in sorted(grupos.items())
    }


def formatar_resumo(resultado: dict, nome_embedder: str) -> str:
    r = resultado["resumo"]

    def pct(v):
        return "n/d" if v is None else f"{v * 100:.1f}%"

    linhas = [
        f"Embedder: {nome_embedder} | k = {r['k']} | perguntas: {r['perguntas']}",
        f"Taxa de acerto geral:              {pct(r['taxa_acerto'])}",
        f"Lembranças corretas:               {pct(r['taxa_lembranca_correta'])}",
        f"Informação desatualizada devolvida: {pct(r['taxa_informacao_desatualizada'])}",
        f"Esquecimento correto:              {pct(r['taxa_esquecimento_correto'])}",
        f"Tokens médios (memória):           {r['tokens_medios_memoria']}",
        f"Tokens médios (histórico completo): {r['tokens_medios_historico_completo']}",
        f"Redução de tokens:                 {r['reducao_tokens_percentual']}%",
        "",
        "Por tipo de pergunta (acertos/total):",
    ]
    for tipo, v in resultado["por_tipo"].items():
        linhas.append(f"  {tipo:<28} {v['acertos']}/{v['perguntas']}")
    return "\n".join(linhas)