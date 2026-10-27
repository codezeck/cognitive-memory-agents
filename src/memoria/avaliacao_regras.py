"""Avalia o baseline por regras em casos de frases e em conversas.

Frases: compara as decisões extraídas com as esperadas (exatidão por frase,
precisão, revocação e F1 sobre as decisões).
Conversas: processa os turnos com `GerenciadorMemoria` e confere o estado da
memória nos pontos de verificação (fatos que devem existir e fatos que devem
ter sumido).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from src.memoria.base import MemoriaLongoPrazo
from src.memoria.gerenciador import GerenciadorMemoria
from src.memoria.regras import Decisao, extrair, normalizar

PASTA = Path(__file__).resolve().parents[2] / "eval" / "memoria" / "regras"


def carregar(nome: str) -> list[dict]:
    with open(PASTA / nome, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _tupla(acao: str, chave, valor) -> tuple:
    return (acao, chave, normalizar(valor) if valor else None)


def _decisoes(ds: list[Decisao]) -> list[tuple]:
    return [_tupla(d.acao, d.chave, d.valor) for d in ds]


def avaliar_frases(casos: list[dict], extrator: Callable = extrair) -> dict:
    tp = fp = fn = acertos = 0
    falhas = []
    for caso in casos:
        obtido = _decisoes(extrator(caso["frase"]))
        esperado = [_tupla(*x) for x in caso["esperado"]]
        so_obtido = set(obtido) - set(esperado)
        so_esperado = set(esperado) - set(obtido)
        tp += len(set(obtido) & set(esperado))
        fp += len(so_obtido)
        fn += len(so_esperado)
        if obtido == esperado:
            acertos += 1
        else:
            falhas.append({
                "id": caso["id"], "frase": caso["frase"],
                "esperado": esperado, "obtido": obtido,
            })
    precisao = tp / (tp + fp) if tp + fp else 1.0
    revocacao = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precisao * revocacao / (precisao + revocacao) if precisao + revocacao else 0.0
    total = len(casos)
    return {
        "casos": total,
        "exatidao_por_frase": round(acertos / total, 4) if total else None,
        "precisao": round(precisao, 4),
        "revocacao": round(revocacao, 4),
        "f1": round(f1, 4),
        "falhas": falhas,
    }


def avaliar_conversas(
    conversas: list[dict], criar_memoria: Callable[[], MemoriaLongoPrazo]
) -> dict:
    total_pontos = pontos_ok = 0
    falhas = []
    for conversa in conversas:
        gerenciador = GerenciadorMemoria(criar_memoria())
        uid = conversa["usuario_id"]
        por_turno: dict[int, list[dict]] = {}
        for ponto in conversa["checkpoints"]:
            por_turno.setdefault(ponto["apos_turno"], []).append(ponto)
        for numero, mensagem in enumerate(conversa["turnos"], start=1):
            gerenciador.processar(uid, mensagem)
            for ponto in por_turno.get(numero, []):
                estado = gerenciador.estado(uid)
                problemas = []
                for chave, valor in ponto["estado"].items():
                    atual = estado.get(chave)
                    if atual is None or normalizar(atual) != normalizar(valor):
                        problemas.append(f"esperava {chave}={valor!r}, obtido {atual!r}")
                for chave in ponto["ausentes"]:
                    if chave in estado:
                        problemas.append(f"{chave} deveria ter sumido (ainda é {estado[chave]!r})")
                total_pontos += 1
                if problemas:
                    falhas.append({
                        "conversa": conversa["id"], "apos_turno": numero,
                        "mensagem": mensagem, "problemas": problemas,
                    })
                else:
                    pontos_ok += 1
    return {
        "conversas": len(conversas),
        "pontos_de_verificacao": total_pontos,
        "pontos_corretos": pontos_ok,
        "taxa_pontos_corretos": round(pontos_ok / total_pontos, 4) if total_pontos else None,
        "falhas": falhas,
    }


def formatar(nome: str, frases: dict, conversas: dict, mostrar_falhas: bool = False) -> str:
    def pct(v):
        return "n/d" if v is None else f"{v * 100:.1f}%"

    linhas = [
        f"=== Conjunto: {nome} ===",
        f"Frases: {frases['casos']} | exatidão por frase: {pct(frases['exatidao_por_frase'])}",
        f"  precisão {pct(frases['precisao'])} | revocação {pct(frases['revocacao'])} | F1 {pct(frases['f1'])}",
        f"Conversas: {conversas['conversas']} | pontos de verificação corretos: "
        f"{conversas['pontos_corretos']}/{conversas['pontos_de_verificacao']} "
        f"({pct(conversas['taxa_pontos_corretos'])})",
    ]
    if mostrar_falhas:
        for f in frases["falhas"]:
            linhas += [f"  [frase] {f['id']}: {f['frase']}",
                       f"      esperado: {f['esperado']}", f"      obtido:   {f['obtido']}"]
        for f in conversas["falhas"]:
            linhas.append(f"  [conversa] {f['conversa']} após o turno {f['apos_turno']} "
                          f"({f['mensagem']!r}): " + "; ".join(f["problemas"]))
    return "\n".join(linhas)
