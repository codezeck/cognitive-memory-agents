
import json
import sys
from pathlib import Path

# Adiciona a raiz do projeto ao caminho de importação.
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src import agent

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.json"



def avaliar_caso(caso):
    # Cada caso começa com um histórico independente.
    agent.historico.clear()
    agent.historico.append({
        "role": "system",
        "content": agent.SYSTEM_PROMPT,
    })

    resposta = ""

    for mensagem in caso["mensagens"]:
        resposta = agent.responder(mensagem)

    esperados = caso["esperado"]

    if isinstance(esperados, str):
        esperados = [esperados]

    passou = any(
        termo.casefold() in resposta.casefold()
        for termo in esperados
    )

    esperado = " | ".join(esperados)

    return {
        "id": caso["id"],
        "categoria": caso["categoria"],
        "passou": passou,
        "esperado": esperado,
        "resposta": resposta,
    }


def main():
    with DATASET_PATH.open("r", encoding="utf-8") as arquivo:
        casos = json.load(arquivo)

    resultados = []

    for caso in casos:
        print(f"\nAvaliando {caso['id']}: {caso['descricao']}")

        try:
            resultado = avaliar_caso(caso)
            resultados.append(resultado)

            status = "PASSOU" if resultado["passou"] else "FALHOU"
            print(f"Resultado: {status}")
            print(f"Esperado: {resultado['esperado']}")
            print(f"Resposta: {resultado['resposta']}")

        except Exception as erro:
            resultados.append({
                "id": caso["id"],
                "categoria": caso["categoria"],
                "passou": False,
                "erro": str(erro),
            })
            print(f"ERRO: {erro}")

    total = len(resultados)
    aprovados = sum(r["passou"] for r in resultados)
    taxa = (aprovados / total * 100) if total else 0

    relatorio = BASE_DIR / "results.json"
    relatorio.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n===== RESUMO DA AVALIAÇÃO =====")
    print(f"Casos avaliados: {total}")
    print(f"Aprovados: {aprovados}")
    print(f"Reprovados: {total - aprovados}")
    print(f"Taxa de aprovação: {taxa:.1f}%")
    print(f"Relatório: {relatorio}")


if __name__ == "__main__":
    main()
