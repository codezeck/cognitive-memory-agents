from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from evaluate import avaliar_resposta

EVAL_DIR = Path(__file__).resolve().parent
DATASET_PATH = EVAL_DIR / "dataset.json"
CENARIOS = ("sem_memoria", "historico_completo", "memoria_persistente_real")
SUFIXOS = {
    "sem_memoria": "sem",
    "historico_completo": "hist",
    "memoria_persistente_real": "mem",
}


def conversar(cliente, usuario_id, mensagem, provedor, modelo):
    resposta = cliente.post(
        "/conversas",
        json={
            "usuario_id": usuario_id,
            "mensagem": mensagem,
            "provedor": provedor,
            "modelo": modelo,
        },
    )
    resposta.raise_for_status()
    return resposta.json()


def metricas(chamadas):
    entradas = [c.get("tokens_entrada") for c in chamadas]
    saidas = [c.get("tokens_saida") for c in chamadas]
    completas = all(v is not None for v in entradas + saidas)
    latencias = [int(c.get("latencia_ms") or 0) for c in chamadas]

    return {
        "tokens_entrada": sum(int(v) for v in entradas) if completas else None,
        "tokens_saida": sum(int(v) for v in saidas) if completas else None,
        "tokens_total": sum(int(v) for v in entradas + saidas) if completas else None,
        "metricas_completas": completas,
        "latencia_api_total_ms": sum(latencias),
        "latencia_api_media_ms": round(mean(latencias), 2) if latencias else 0,
        "chamadas_modelo": len(chamadas),
    }


def executar_cenario(cliente, caso, cenario, usuario_id, provedor, modelo):
    inicio = time.perf_counter()
    chamadas = []
    ids_memoria = []
    memorias_esperadas = caso.get("memorias", [])

    if cenario == "sem_memoria":
        chamadas.append(
            conversar(
                cliente, usuario_id, caso["mensagens"][-1], provedor, modelo
            )
        )

    elif cenario == "historico_completo":
        for mensagem in caso["mensagens"]:
            chamadas.append(
                conversar(cliente, usuario_id, mensagem, provedor, modelo)
            )

    elif cenario == "memoria_persistente_real":
        for indice, texto in enumerate(memorias_esperadas, start=1):
            resposta = cliente.post(
                f"/usuarios/{usuario_id}/memorias",
                json={
                    "texto": texto,
                    "chave": f"{caso['id']}_{indice}",
                },
            )
            resposta.raise_for_status()
            ids_memoria.append(resposta.json()["id"])

        # Limpa o historico da conversa sem apagar as memorias cadastradas.
        sessao = cliente.post(f"/usuarios/{usuario_id}/sessoes")
        sessao.raise_for_status()

        chamadas.append(
            conversar(
                cliente, usuario_id, caso["mensagens"][-1], provedor, modelo
            )
        )

    else:
        raise ValueError(f"Cenario desconhecido: {cenario}")

    final = chamadas[-1]
    usadas = final.get("memorias_usadas", [])

    recuperacao_ok = None
    if cenario == "memoria_persistente_real" and memorias_esperadas:
        recuperacao_ok = all(
            any(esperada.strip() == usada.strip() for usada in usadas)
            for esperada in memorias_esperadas
        )

    return {
        "id": caso["id"],
        "categoria": caso["categoria"],
        "cenario": cenario,
        "passou": avaliar_resposta(final["resposta"], caso["esperado"]),
        "esperado": caso["esperado"],
        "resposta": final["resposta"],
        "memorias_esperadas": memorias_esperadas,
        "memorias_usadas": usadas,
        "ids_memoria_criados": ids_memoria,
        "recuperacao_memoria_ok": recuperacao_ok,
        "tempo_execucao_ms": round((time.perf_counter() - inicio) * 1000, 2),
        **metricas(chamadas),
    }


def resumir(resultados):
    resumo = {}

    for cenario in CENARIOS:
        grupo = [r for r in resultados if r["cenario"] == cenario]
        validos = [r for r in grupo if "erro" not in r]
        completos = [r for r in validos if r["metricas_completas"]]
        latencias = [r["latencia_api_total_ms"] for r in validos]
        aprovados = sum(bool(r["passou"]) for r in validos)

        casos_memoria = [
            r for r in validos
            if cenario == "memoria_persistente_real"
            and r["memorias_esperadas"]
        ]

        resumo[cenario] = {
            "casos": len(grupo),
            "executados": len(validos),
            "aprovados": aprovados,
            "erros": len(grupo) - len(validos),
            "taxa_aprovacao": round(aprovados / len(validos) * 100, 2)
            if validos else 0,
            "tokens_entrada_total": sum(r["tokens_entrada"] for r in completos),
            "tokens_saida_total": sum(r["tokens_saida"] for r in completos),
            "tokens_total": sum(r["tokens_total"] for r in completos),
            "casos_com_metricas_incompletas": len(validos) - len(completos),
            "chamadas_modelo": sum(r["chamadas_modelo"] for r in validos),
            "latencia_api_total_ms": sum(latencias),
            "latencia_api_media_por_caso_ms": round(mean(latencias), 2)
            if latencias else 0,
            "casos_com_memoria_esperada": len(casos_memoria),
            "memorias_recuperadas_corretamente": sum(
                r["recuperacao_memoria_ok"] is True for r in casos_memoria
            ),
            "taxa_recuperacao_memoria": round(
                sum(r["recuperacao_memoria_ok"] is True for r in casos_memoria)
                / len(casos_memoria) * 100,
                2,
            ) if casos_memoria else None,
        }

    return resumo


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark dos cenarios do agente pela API real."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--provedor", default="ollama")
    parser.add_argument("--modelo", default="qwen2.5-coder:3b")
    parser.add_argument("--repeticoes", type=int, default=1)
    parser.add_argument(
        "--saida",
        default="eval/results_api_real.json",
        help="Arquivo de saida; nao sobrescreve um resultado existente.",
    )
    args = parser.parse_args()

    if args.repeticoes < 1:
        parser.error("--repeticoes precisa ser pelo menos 1.")

    saida = Path(args.saida)
    if not saida.is_absolute():
        saida = ROOT_DIR / saida
    if saida.exists():
        raise SystemExit(
            f"O arquivo {saida} ja existe. Escolha outro caminho com --saida."
        )

    casos = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    resultados = []
    execucao_id = uuid.uuid4().hex[:8]

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=120) as cliente:
        try:
            saude = cliente.get("/saude")
            saude.raise_for_status()
            if saude.json().get("status") != "ok":
                raise RuntimeError("Endpoint /saude nao retornou status ok.")
        except Exception as erro:
            print(f"API indisponivel: {erro}")
            return 2

        for repeticao in range(1, args.repeticoes + 1):
            for caso in casos:
                for cenario in CENARIOS:
                    usuario_id = (
                        f"eval_{execucao_id}_{caso['id'].lower()}_"
                        f"{SUFIXOS[cenario]}_r{repeticao}"
                    )
                    registro = None

                    print(
                        f"\nRepeticao {repeticao}/{args.repeticoes} | "
                        f"{caso['id']} | {cenario}"
                    )

                    try:
                        registro = executar_cenario(
                            cliente, caso, cenario, usuario_id,
                            args.provedor, args.modelo,
                        )
                        registro["repeticao"] = repeticao
                        print(
                            f"{'PASSOU' if registro['passou'] else 'FALHOU'}: "
                            f"{registro['resposta']}"
                        )
                        print(
                            f"Tokens: {registro['tokens_total']} | "
                            f"latencia: {registro['latencia_api_total_ms']} ms"
                        )
                    except Exception as erro:
                        registro = {
                            "id": caso["id"],
                            "categoria": caso["categoria"],
                            "cenario": cenario,
                            "repeticao": repeticao,
                            "passou": False,
                            "erro": str(erro)[:500],
                        }
                        print(f"ERRO: {erro}")
                    finally:
                        # Apaga as memorias e o historico do usuario sintetico.
                        try:
                            cliente.delete(f"/usuarios/{usuario_id}/memorias")
                        except Exception as erro:
                            if registro is not None:
                                registro["erro_limpeza"] = str(erro)[:300]

                    resultados.append(registro)

    relatorio = {
        "data_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "provedor": args.provedor,
        "modelo": args.modelo,
        "repeticoes": args.repeticoes,
        "dataset": "eval/dataset.json",
        "observacoes": [
            "Usa a API e o armazenamento configurados no servidor.",
            "As memorias do cenario persistente sao cadastradas manualmente via API.",
            "Nao avalia extracao automatica de fatos a partir da conversa.",
            "O cenario historico_completo acumula chamadas sequenciais.",
            "Os usuarios sao sinteticos; o script tenta apagar suas memorias ao final.",
            "Tokens sao somados apenas quando as metricas estao completas.",
        ],
        "resultados": resultados,
        "resumo": resumir(resultados),
    }

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n===== RESUMO =====")
    for cenario, dados in relatorio["resumo"].items():
        print(
            f"{cenario}: {dados['aprovados']}/{dados['executados']} aprovados; "
            f"tokens={dados['tokens_total']}; "
            f"latencia media/caso={dados['latencia_api_media_por_caso_ms']} ms"
        )
        if cenario == "memoria_persistente_real":
            print(
                "Recuperacao de memorias: "
                f"{dados['memorias_recuperadas_corretamente']}/"
                f"{dados['casos_com_memoria_esperada']}"
            )

    print(f"\nRelatorio salvo em: {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())