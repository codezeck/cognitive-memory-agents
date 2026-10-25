
import argparse
import json
import sys
import re
import time
from pathlib import Path
from statistics import mean

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src import agent

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.json"
RESULTS_PATH = BASE_DIR / "results.json"

CENARIOS = [
    "sem_memoria",
    "historico_completo",
    "memoria_externa",
]


def campo(resposta, nome, padrao=0):
    if isinstance(resposta, dict):
        return resposta.get(nome, padrao) or padrao
    return getattr(resposta, nome, padrao) or padrao



def executar_modelo(mensagens):
    inicio = time.perf_counter()

    resultado = agent.modelo_ia.gerar_com_detalhes(
        mensagens,
        options={"temperature": 0},
    )

    tempo_ms = (time.perf_counter() - inicio) * 1000

    return {
        "resposta": resultado["resposta"],
        "tokens_entrada": int(resultado["tokens_entrada"]),
        "tokens_saida": int(resultado["tokens_saida"]),
        "tempo_ms": round(tempo_ms, 2),
    }




def avaliar_resposta(resposta, esperados):
    texto = resposta.casefold().strip()

    if isinstance(esperados, str):
        termos = [esperados]
    else:
        termos = esperados

    indicadores_desconhecido = [
        "não sei",
        "nao sei",
        "não tenho essa informação",
        "nao tenho essa informacao",
        "não tenho informações",
        "nao tenho informacoes",
        "não há informações suficientes",
        "nao ha informacoes suficientes",
        "não tenho informação",
        "nao tenho informacao",
        "não tenho informações sobre",
        "nao tenho informacoes sobre",
        "não tenho acesso ao histórico",
        "nao tenho acesso ao historico",
        "não tenho acesso a essa informação",
        "nao tenho acesso a essa informacao",
        "não consigo determinar",
        "nao consigo determinar",
        "não é possível determinar",
        "nao e possivel determinar",
    ]

    # Caso de avaliação de informação desconhecida.
    espera_desconhecimento = any(
        termo.casefold().strip() in ("não sei", "nao sei")
        for termo in termos
    )

    if espera_desconhecimento:
        admite_desconhecimento = any(
            indicador in texto
            for indicador in indicadores_desconhecido
        )

        inventa_nome = (
            "seu primeiro professor foi" in texto
            or "o nome do seu primeiro professor foi" in texto
        )

        return admite_desconhecimento and not inventa_nome

    # Reprova quando o termo esperado aparece em uma negação direta.
    for termo in termos:
        termo_normalizado = termo.casefold().strip()

        padrao_negacao = (
            r"\bnão\b.{0,30}\b"
            + re.escape(termo_normalizado)
            + r"\b"
        )

        if re.search(padrao_negacao, texto):
            return False

    return all(
        termo.casefold() in texto
        for termo in termos
    )


def avaliar_sem_memoria(caso):
    mensagens = [
        {"role": "system", "content": agent.SYSTEM_PROMPT},
        {"role": "user", "content": caso["mensagens"][-1]},
    ]

    resultado = executar_modelo(mensagens)
    return resultado, 1


def avaliar_historico(caso):
    mensagens = [
        {"role": "system", "content": agent.SYSTEM_PROMPT}
    ]

    tokens_entrada = 0
    tokens_saida = 0
    tempo_ms = 0
    chamadas = 0
    resposta_final = ""

    for mensagem in caso["mensagens"]:
        mensagens.append({"role": "user", "content": mensagem})

        resultado = executar_modelo(mensagens)

        resposta_final = resultado["resposta"]
        tokens_entrada += resultado["tokens_entrada"]
        tokens_saida += resultado["tokens_saida"]
        tempo_ms += resultado["tempo_ms"]
        chamadas += 1

        mensagens.append({
            "role": "assistant",
            "content": resposta_final,
        })

    return {
        "resposta": resposta_final,
        "tokens_entrada": tokens_entrada,
        "tokens_saida": tokens_saida,
        "tempo_ms": round(tempo_ms, 2),
    }, chamadas


def avaliar_memoria_externa(caso):
    memorias = caso.get("memorias", [])
    contexto = agent.formatar_memorias(memorias)

    mensagens = [
        {"role": "system", "content": agent.SYSTEM_PROMPT}
    ]

    if contexto:
        mensagens.append({
            "role": "system",
            "content": f"Contexto de memória:\n{contexto}",
        })

    mensagens.append({
        "role": "user",
        "content": caso["mensagens"][-1],
    })

    resultado = executar_modelo(mensagens)
    return resultado, 1


def avaliar_caso(caso, cenario):
    if cenario == "sem_memoria":
        resultado, chamadas = avaliar_sem_memoria(caso)
    elif cenario == "historico_completo":
        resultado, chamadas = avaliar_historico(caso)
    elif cenario == "memoria_externa":
        resultado, chamadas = avaliar_memoria_externa(caso)
    else:
        raise ValueError(f"Cenário desconhecido: {cenario}")

    passou = avaliar_resposta(
        resultado["resposta"],
        caso["esperado"],
    )

    return {
        "id": caso["id"],
        "categoria": caso["categoria"],
        "cenario": cenario,
        "passou": passou,
        "esperado": caso["esperado"],
        **resultado,
        "tokens_total": (
            resultado["tokens_entrada"]
            + resultado["tokens_saida"]
        ),
        "chamadas_modelo": chamadas,
    }


def resumir(resultados):
    resumo = {}

    for cenario in CENARIOS:
        grupo = [
            r for r in resultados
            if r["cenario"] == cenario
        ]

        erros = sum(1 for r in grupo if "erro" in r)

        taxa_erro = (
        round(erros / len(grupo) * 100, 2)
        if grupo else 0
)

        validos = [r for r in grupo if "erro" not in r]
        total = len(validos)

        resumo[cenario] = {
            "casos": len(grupo),
            "executados": total,
            "aprovados": sum(r["passou"] for r in validos),
            "erros": erros,
            "taxa_erro": taxa_erro,
            "taxa_aprovacao": round(
                sum(r["passou"] for r in validos) / total * 100, 2
            ) if total else 0,
            "tokens_entrada_total": sum(
                r["tokens_entrada"] for r in validos
            ),
            "tokens_saida_total": sum(
                r["tokens_saida"] for r in validos
            ),
            "tokens_total": sum(
                r["tokens_total"] for r in validos
            ),
            "tempo_total_ms": round(
                sum(r["tempo_ms"] for r in validos), 2
            ),
            "chamadas_modelo": sum(
                r["chamadas_modelo"] for r in validos
            ),
            "tempo_medio_ms": round(
                mean(r["tempo_ms"] for r in validos), 2
            ) if validos else 0,
        }

    return resumo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repeticoes",
        type=int,
        default=1,
        help="Número de vezes que cada cenário será testado.",
    )
    args = parser.parse_args()

    if args.repeticoes < 1:
        parser.error("--repeticoes precisa ser pelo menos 1.")

    with DATASET_PATH.open("r", encoding="utf-8") as arquivo:
        casos = json.load(arquivo)

    resultados = []

    for repeticao in range(1, args.repeticoes + 1):
        for caso in casos:
            for cenario in CENARIOS:
                print(
                    f"\nRepetição {repeticao}/{args.repeticoes} | "
                    f"{caso['id']} | {cenario}"
                )

                try:
                    resultado = avaliar_caso(caso, cenario)
                    resultado["repeticao"] = repeticao
                    resultados.append(resultado)

                    status = "PASSOU" if resultado["passou"] else "FALHOU"
                    print(f"{status}: {resultado['resposta']}")
                    print(
                        f"Tokens: {resultado['tokens_total']} "
                        f"(entrada {resultado['tokens_entrada']}, "
                        f"saída {resultado['tokens_saida']})"
                    )

                except Exception as erro:
                    resultados.append({
                        "id": caso["id"],
                        "categoria": caso["categoria"],
                        "cenario": cenario,
                        "repeticao": repeticao,
                        "passou": False,
                        "erro": str(erro),
                    })
                    print(f"ERRO: {erro}")

    relatorio = {
        "modelo": agent.MODEL,
        "repeticoes": args.repeticoes,
        "observacao": (
            "Memória externa simulada; não representa integração "
            "com a API real. Tokens e tempos incluem as chamadas "
            "registradas pelo avaliador."
        ),
        "resultados": resultados,
        "resumo": resumir(resultados),
    }

    RESULTS_PATH.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n===== RESUMO COMPARATIVO =====")

    for cenario, dados in relatorio["resumo"].items():
        print(f"\n{cenario}")
        print(f"Taxa de acerto: {dados['taxa_aprovacao']}%")
        print(f"Tokens totais: {dados['tokens_total']}")
        print(f"Chamadas ao modelo: {dados['chamadas_modelo']}")
        print(f"Tempo total: {dados['tempo_total_ms']} ms")

    print(f"\nRelatório salvo em: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
