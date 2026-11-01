from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from eval.evaluate import avaliar_resposta

USUARIO_ID = "eval_comparativo"
DATASET = ROOT_DIR / "eval" / "dataset_comparativo.json"

CENARIOS = (
    "sem_memoria",
    "historico_completo",
    "memoria_persistente_api",
    "memoria_regras_api",
)

CENARIOS_MEMORIA = {
    "memoria_persistente_api",
    "memoria_regras_api",
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(
        c for c in texto if not unicodedata.combining(c)
    )


def carregar_token() -> str:
    """Lê o token do usuário sintético sem mostrá-lo no terminal."""
    caminho = ROOT_DIR / ".env"

    if not caminho.exists():
        raise RuntimeError(
            "Arquivo .env não encontrado. Configure API_TOKENS localmente."
        )

    valor = None
    for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
        if linha.strip().startswith("API_TOKENS="):
            valor = linha.split("=", 1)[1].strip().strip('"').strip("'")
            break

    if valor is None:
        raise RuntimeError("API_TOKENS não encontrado no .env.")

    for item in valor.split(","):
        token, separador, usuario = item.strip().partition(":")
        if separador and usuario.strip() == USUARIO_ID and token.strip():
            return token.strip()

    raise RuntimeError(
        f"Não existe token configurado para o usuário sintético {USUARIO_ID!r}."
    )


def limpar_usuario(cliente: httpx.Client) -> None:
    """Limpa exclusivamente o usuário sintético dedicado ao benchmark."""
    resposta = cliente.delete(
        f"/usuarios/{USUARIO_ID}/memorias"
    )
    resposta.raise_for_status()

    sessao = cliente.post(
        f"/usuarios/{USUARIO_ID}/sessoes"
    )
    sessao.raise_for_status()


def conversar(
    cliente: httpx.Client,
    mensagem: str,
    provedor: str,
    modelo: str,
) -> dict:
    resposta = cliente.post(
        "/conversas",
        json={
            "usuario_id": USUARIO_ID,
            "mensagem": mensagem,
            "provedor": provedor,
            "modelo": modelo,
        },
    )
    resposta.raise_for_status()
    return resposta.json()


def iniciar_nova_sessao(cliente: httpx.Client) -> None:
    resposta = cliente.post(f"/usuarios/{USUARIO_ID}/sessoes")
    resposta.raise_for_status()


def obter_estado_regras(cliente: httpx.Client) -> dict:
    resposta = cliente.get(f"/usuarios/{USUARIO_ID}/estado-regras")
    resposta.raise_for_status()
    estado = resposta.json()
    if not isinstance(estado, dict):
        raise ValueError("Estado das regras retornado em formato inv?lido.")
    return estado


def criar_memoria(
    cliente: httpx.Client,
    texto: str,
    chave: str | None = None,
) -> str:
    resposta = cliente.post(
        f"/usuarios/{USUARIO_ID}/memorias",
        json={"texto": texto, "chave": chave},
    )
    resposta.raise_for_status()
    return resposta.json()["id"]


def apagar_memoria(cliente: httpx.Client, memoria_id: str) -> None:
    resposta = cliente.delete(
        f"/usuarios/{USUARIO_ID}/memorias/{memoria_id}"
    )
    resposta.raise_for_status()


def normalizar_memoria_equivalente(texto: str) -> str:
    """Normaliza apenas variantes conhecidas de fatos de memória."""
    import re

    texto_normalizado = normalizar(texto).strip()
    texto_normalizado = re.sub(r"\\s+", " ", texto_normalizado)

    padroes = [
        (r"(?:moro em|mora em) (.+?)[.!]?", "cidade"),
        (r"(?:pratico|pratica) (.+?)[.!]?", "esporte"),
        (r"meu carro e um (.+?)[.!]?", "carro"),
        (r"carro:\s*(.+?)[.!]?", "carro"),
        (r"meu nome e (.+?)[.!]?", "nome"),
        (r"chama[- ]se (.+?)[.!]?", "nome"),
    ]

    for padrao, categoria in padroes:
        correspondencia = re.fullmatch(padrao, texto_normalizado)
        if correspondencia:
            valor = correspondencia.group(1).strip(" .!")
            if valor:
                return f"{categoria}:{valor}"

    return texto_normalizado.strip(" .! ")


def avaliar_recuperacao_equivalente(
    esperadas: list[str], usadas: list[str]
) -> bool:
    """Compara fatos equivalentes sem ignorar extras ou duplicados."""
    esperadas_normalizadas = sorted(
        normalizar_memoria_equivalente(item) for item in esperadas
    )
    usadas_normalizadas = sorted(
        normalizar_memoria_equivalente(item) for item in usadas
    )
    return esperadas_normalizadas == usadas_normalizadas


def texto_memoria(chave: str, valor: str) -> str:
    """Converte o estado das regras em fatos legíveis pelo agente."""
    modelos = {
        "cidade": "Moro em {v}.",
        "profissao": "Trabalho como {v}.",
        "nome": "Meu nome é {v}.",
        "apelido": "Pode me chamar de {v}.",
        "esporte": "Pratico {v}.",
        "carro": "Meu carro é um {v}.",
        "time": "Meu time do coração é {v}.",
        "filhos": "Tenho {v} filhos.",
        "viagem": "Planejo viajar para {v}.",
    }

    if chave in modelos:
        return modelos[chave].format(v=valor)

    if chave.startswith("pet:"):
        partes = chave.split(":", 2)
        if len(partes) == 3:
            especie = partes[1]
            return f"Meu {especie} se chama {valor}."

    if chave.startswith("gosto:"):
        return f"Gosto de {valor}."

    if chave.startswith("favorito:"):
        categoria = chave.split(":", 1)[1]
        return f"Meu favorito em {categoria} é {valor}."

    return f"Fato sobre {chave}: {valor}."


def resposta_esperada_cenario(caso: dict, cenario: str) -> str:
    if cenario == "sem_memoria":
        return "DESCONHECIDO"

    esperado = caso["esperado"]

    if isinstance(esperado, list):
        return "DESCONHECIDO"

    return str(esperado)


def avaliar_resposta_controlada(resposta: str, esperado: str) -> bool:
    def limpar(texto: str) -> str:
        return normalizar(texto).strip(" \t\r\n.,!?;:'\"`")

    return limpar(resposta) == limpar(esperado)


def avaliar_resposta_comparativo(
    resposta: str,
    caso: dict,
) -> bool:
    """Avalia respostas desconhecidas sem aceitar vazamento de fatos."""
    esperado = caso["esperado"]

    espera_desconhecimento = (
        isinstance(esperado, list)
        and any(
            normalizar(str(item)).strip(" \t\r\n.,!?;:'\"`")
            in {"nao sei", "desconhecido", "informacao desconhecida"}
            for item in esperado
        )
    )

    if not espera_desconhecimento:
        return avaliar_resposta(resposta, esperado)

    texto = normalizar(resposta).strip()
    mensagens = caso.get("mensagens", [])
    contexto = normalizar(" ".join(mensagens))
    mensagens_anteriores = [
        normalizar(m) for m in mensagens[:-1]
    ]

    # Rejeita a divulga??o dos fatos expl?citos que deveriam ser esquecidos.
    fatos_esquecidos = []
    padroes_fatos = (
        r"\b(?:moro|vivo|resido)\s+em\s+(.+?)(?:[.!?]|$)",
        r"\btorco\s+(?:pelo|pela|pro|para|por|pra)\s+(.+?)(?:[.!?]|$)",
    )
    for mensagem in mensagens_anteriores:
        for padrao in padroes_fatos:
            for match in re.finditer(padrao, mensagem):
                valor = match.group(1).strip(" .,!?:;")
                if valor:
                    fatos_esquecidos.append(valor)

    for valor in fatos_esquecidos:
        if re.search(rf"\b{re.escape(valor)}\b", texto):
            return False

    # Rejeita afirma??es de fatos pessoais, inclusive valores inventados.
    dominios = set()
    if any(t in contexto for t in ("cidade", "moro em", "mora em", "vivo em")):
        dominios.add("cidade")
    if "time" in contexto or "torc" in contexto:
        dominios.add("time")
    if any(t in contexto for t in ("esporte", "pratico", "yoga")):
        dominios.add("esporte")
    if "carro" in contexto:
        dominios.add("carro")
    if "nome" in contexto:
        dominios.add("nome")

    afirmacoes = {
        "cidade": (
            r"\b(?:(?:voce|eu)\s+)?(?:moro|mora|vivo|vive|resido|reside)"
            r"\s+(?:(?:atualmente|agora)\s+)?(?:em|na|no|nos|nas)\s+"
            r"[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,3}\b",
            r"\b(?:(?:voce|eu)\s+)?(?:estou morando|esta morando|estou|esta)"
            r"\s+(?:(?:atualmente|agora)\s+)?(?:em|na|no|nos|nas)\s+"
            r"[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,3}\b",
        ),
        "time": (
            r"\b(?:(?:voce|eu)\s+)?(?:torco|torce|torcia)\s+"
            r"(?:mais\s+)?(?:pelo|pela|pro|para|por|pra)\s+"
            r"(?:o\s+|a\s+)?[a-z][a-z-]*\b",
            r"\b(?:seu|meu)\s+time\s+(?:e|seria)\s+"
            r"(?:o\s+|a\s+)?[a-z][a-z-]*\b",
        ),
        "esporte": (
            r"\b(?:(?:voce|eu)\s+)?(?:pratico|pratica|praticando)\s+"
            r"(?:o\s+)?[a-z][a-z-]*\b",
            r"\bo esporte que (?:voce|eu)\s+pratica\s+"
            r"(?:e|seria)\s+(?:o\s+)?[a-z][a-z-]*\b",
        ),
        "carro": (
            r"\b(?:seu|meu)\s+carro\s+(?:atual\s+)?(?:e|seria)\s+"
            r"(?:um\s+)?[a-z][a-z0-9-]*(?:\s+[a-z0-9-]+){0,3}\b",
        ),
        "nome": (
            r"\b(?:seu|meu)\s+nome\s+(?:e|seria)\s+[a-z][a-z-]*\b",
        ),
    }

    for dominio in dominios:
        for padrao in afirmacoes.get(dominio, ()):
            if re.search(padrao, texto):
                return False

    # Respostas naturais que indicam falta de conhecimento.
    padroes_desconhecimento = (
        r"\bnao sei\b",
        r"\bdesconhecido\b",
        r"\b(?:nao tenho|nao ha|sem)\b.{0,100}"
        r"\b(?:informacao|informacoes|dados|registro|historico|contexto|memoria)\b",
        r"\bnao posso fornecer\b.{0,100}\b(?:informacao|informacoes|dados)\b",
        r"\bnao consigo determinar\b",
        r"\b(?:informacoes|dados)\s+insuficientes\b",
        r"\b(?:historico|memoria)\b.{0,80}\bnao (?:contem|tem|possui)\b",
        r"\bnao posso (?:reconhecer|identificar|determinar|lembrar)\b",
        r"\bnao forneceu\b.{0,100}\b(?:local|cidade|informacao|informacoes|dados|historico|contexto)\b",
        r"\bnao posso lembrar\b",
        r"\bnao (?:tenho|tem|ha)\b.{0,100}"
        r"\b(?:informacoes|dados)\b.{0,50}\b(?:atualizadas|atualizados)\b",
        r"\bnao posso fornecer informacoes pessoais\b",
        r"\bnao me deixou\b.{0,80}\b(?:informacao|informacoes|dados|contexto)\b",
    )

    return any(
        re.search(padrao, texto)
        for padrao in padroes_desconhecimento
    )

def metricas(chamadas: list[dict]) -> dict:
    entradas = [c.get("tokens_entrada") for c in chamadas]
    saidas = [c.get("tokens_saida") for c in chamadas]
    completas = bool(chamadas) and all(
        valor is not None for valor in entradas + saidas
    )
    latencias = [int(c.get("latencia_ms") or 0) for c in chamadas]

    return {
        "tokens_entrada": (
            sum(int(v) for v in entradas) if completas else None
        ),
        "tokens_saida": (
            sum(int(v) for v in saidas) if completas else None
        ),
        "tokens_total": (
            sum(int(v) for v in entradas + saidas)
            if completas else None
        ),
        "metricas_completas": completas,
        "latencia_api_total_ms": sum(latencias),
        "latencia_api_media_ms": round(mean(latencias), 2) if latencias else 0,
        "chamadas_modelo": len(chamadas),
    }


def executar_cenario(
    cliente: httpx.Client,
    caso: dict,
    cenario: str,
    provedor: str,
    modelo: str,
) -> dict:
    inicio = time.perf_counter()
    chamadas = []
    estado_regras = None
    estado_regras_ok = None
    memorias_esperadas = caso.get("memorias", [])
    esperado_cenario = resposta_esperada_cenario(caso, cenario)

    try:
        limpar_usuario(cliente)

        if cenario == "sem_memoria":
            # Não envia fatos anteriores nem mantém histórico entre casos.
            chamadas.append(
                conversar(cliente, caso["mensagens"][-1], provedor, modelo)
            )

        elif cenario == "historico_completo":
            for mensagem in caso["mensagens"]:
                chamadas.append(
                    conversar(cliente, mensagem, provedor, modelo)
                )

        elif cenario == "memoria_persistente_api":
            # Insere o estado-ouro do caso manualmente pela API.
            for indice, texto in enumerate(memorias_esperadas, start=1):
                criar_memoria(
                    cliente,
                    texto,
                    chave=f"seed_{caso['id']}_{indice}",
                )

            chamadas.append(
                conversar(cliente, caso["mensagens"][-1], provedor, modelo)
            )


        elif cenario == "memoria_regras_api":
            # Processa mensagens anteriores pelo fluxo real da API.
            # A própria rota /conversas aciona o gerenciador automático.
            for mensagem in caso["mensagens"][:-1]:
                chamadas.append(
                    conversar(cliente, mensagem, provedor, modelo)
                )

            # Limpa apenas o histórico do agente; preserva as memórias.
            iniciar_nova_sessao(cliente)

            # Faz a pergunta final sem o histórico conversacional anterior.
            chamadas.append(
                conversar(
                    cliente,
                    caso["mensagens"][-1],
                    provedor,
                    modelo,
                )
            )
        else:
            raise ValueError(f"Cenário desconhecido: {cenario}")

        final = chamadas[-1]
        usadas = final.get("memorias_usadas", [])

        caso_avaliacao = dict(caso)

        if cenario == "sem_memoria":
            caso_avaliacao["esperado"] = ["não sei"]

        recuperacao_ok = None
        recuperacao_equivalente_ok = None
        if cenario in CENARIOS_MEMORIA:
            # Métrica original: comparação textual estrita.
            recuperacao_ok = set(memorias_esperadas) == set(usadas)
            # Métrica complementar: formatos conhecidos equivalentes.
            recuperacao_equivalente_ok = avaliar_recuperacao_equivalente(
                memorias_esperadas, usadas
            )

        if cenario == "memoria_regras_api":
            estado_regras = obter_estado_regras(cliente)
            estado_regras_ok = (
                estado_regras == caso.get("estado_regras_esperado", {})
            )

        registro = {
            "id": caso["id"],
            "categoria": caso["categoria"],
            "cenario": cenario,
            "repeticao": None,
            "passou": avaliar_resposta_comparativo(
                final["resposta"],
                caso_avaliacao,
            ),
            "esperado": esperado_cenario,
            "resposta": final["resposta"],
            "memorias_esperadas": memorias_esperadas,
            "memorias_usadas": usadas,
            "recuperacao_memoria_ok": recuperacao_ok,
            "recuperacao_equivalente_ok": recuperacao_equivalente_ok,
            "estado_regras_esperado": (
                caso["estado_regras_esperado"]
                if cenario == "memoria_regras_api" else None
            ),
            "estado_regras_obtido": estado_regras,
            "estado_regras_ok": estado_regras_ok,
            "tempo_execucao_ms": round(
                (time.perf_counter() - inicio) * 1000, 2
            ),
            **metricas(chamadas),
        }
        return registro

    finally:
        # O usuário é dedicado ao benchmark; a limpeza limita-se a ele.
        try:
            limpar_usuario(cliente)
        except Exception as erro:
            print(f"AVISO: não foi possível limpar o usuário sintético: {erro}")



def resumir(resultados: list[dict]) -> dict:
    resumo = {}

    for cenario in CENARIOS:
        grupo = [r for r in resultados if r["cenario"] == cenario]
        validos = [r for r in grupo if "erro" not in r]
        falhas = [r for r in grupo if "erro" in r]

        com_memoria = [
            r for r in validos
            if r.get("memorias_esperadas")
            and r.get("recuperacao_memoria_ok") is not None
        ]
        sem_memoria_esperada = [
            r for r in validos
            if not r.get("memorias_esperadas")
            and r.get("recuperacao_memoria_ok") is not None
        ]
        estados = [
            r for r in validos
            if r.get("estado_regras_ok") is not None
        ]
        tokens = [
            r["tokens_total"] for r in validos
            if r.get("tokens_total") is not None
        ]
        latencias = [
            r["latencia_api_total_ms"] for r in validos
            if r.get("latencia_api_total_ms") is not None
        ]

        aprovados = sum(bool(r.get("passou")) for r in grupo)

        resumo[cenario] = {
            "casos": len(grupo),
            "executados": len(validos),
            "falhas": len(falhas),
            "aprovados": aprovados,
            "taxa_aprovacao_pct": (
                round(100 * aprovados / len(grupo), 2)
                if grupo else None
            ),
            "tokens_total": sum(tokens),
            "casos_com_metricas_incompletas": sum(
                not r.get("metricas_completas", False)
                for r in validos
            ),
            "latencia_api_media_por_caso_ms": (
                round(sum(latencias) / len(latencias), 2)
                if latencias else None
            ),
            "casos_com_memoria_esperada": len(com_memoria),
            "memorias_recuperadas_exatamente": sum(
                r["recuperacao_memoria_ok"] is True
                for r in com_memoria
            ),
            "taxa_recuperacao_exata_pct": (
                round(
                    100 * sum(
                        r["recuperacao_memoria_ok"] is True
                        for r in com_memoria
                    ) / len(com_memoria),
                    2,
                )
                if com_memoria else None
            ),
            "memorias_recuperadas_equivalentes": sum(
                r.get("recuperacao_equivalente_ok") is True
                for r in com_memoria
            ),
            "taxa_recuperacao_equivalente_pct": (
                round(
                    100 * sum(
                        r.get("recuperacao_equivalente_ok") is True
                        for r in com_memoria
                    ) / len(com_memoria),
                    2,
                )
                if com_memoria else None
            ),
            "casos_sem_memoria_esperada": len(sem_memoria_esperada),
            "casos_sem_residuos_memoria": sum(
                r["recuperacao_memoria_ok"] is True
                for r in sem_memoria_esperada
            ),
            "estados_regras_verificados": len(estados),
            "estados_regras_corretos": sum(
                r["estado_regras_ok"] is True
                for r in estados
            ),
        }

    return resumo




def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compara quatro estratégias de memória pela API autenticada."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--provedor", default="ollama")
    parser.add_argument("--modelo", default="qwen2.5-coder:3b")
    parser.add_argument("--repeticoes", type=int, default=1)
    parser.add_argument(
        "--saida",
        default="eval/results_comparativo_api.json",
        help="Arquivo novo de saída; não sobrescreve resultados existentes.",
    )
    args = parser.parse_args()

    if args.repeticoes < 1:
        parser.error("--repeticoes precisa ser pelo menos 1.")

    saida = Path(args.saida)
    if not saida.is_absolute():
        saida = ROOT_DIR / saida
    if saida.exists():
        raise SystemExit(
            f"O arquivo {saida} já existe. Escolha outro caminho com --saida."
        )

    casos = json.loads(DATASET.read_text(encoding="utf-8"))
    token = carregar_token()
    resultados = []

    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(
        base_url=args.base_url.rstrip("/"),
        headers=headers,
        timeout=120,
    ) as cliente:
        saude = cliente.get("/saude")
        saude.raise_for_status()
        if saude.json().get("status") != "ok":
            raise RuntimeError("API não retornou status ok.")

        # Confirma token e vínculo com o usuário sem alterar dados.
        teste = cliente.get(
            f"/usuarios/{USUARIO_ID}/memorias",
            params={"consulta": "validacao de autenticacao"},
        )
        teste.raise_for_status()

        for repeticao in range(1, args.repeticoes + 1):
            for caso in casos:
                for cenario in CENARIOS:
                    print(
                        f"\nRepetição {repeticao}/{args.repeticoes} | "
                        f"{caso['id']} | {cenario}"
                    )
                    try:
                        registro = executar_cenario(
                            cliente,
                            caso,
                            cenario,
                            args.provedor,
                            args.modelo,
                        )
                        registro["repeticao"] = repeticao
                        print(
                            f"{'PASSOU' if registro['passou'] else 'FALHOU'}: "
                            f"{registro['resposta']}"
                        )
                        if registro.get("estado_regras_ok") is not None:
                            print(
                                "Estado das regras: "
                                f"{'CORRETO' if registro['estado_regras_ok'] else 'INCORRETO'}"
                            )
                        print(
                            f"Tokens: {registro['tokens_total']} | "
                            f"latência API: {registro['latencia_api_total_ms']} ms"
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

                    resultados.append(registro)

    documento = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "dataset": str(DATASET.relative_to(ROOT_DIR)),
        "usuario_sintetico": USUARIO_ID,
        "observacoes": [
            "Sem memória envia apenas a pergunta final.",
            "Histórico completo envia todas as mensagens pela API.",
            "memoria_regras_api envia mensagens anteriores pela API, reinicia a sessão antes da pergunta final e preserva as memórias persistidas.",
            "Por isso, historico_completo combina histórico conversacional e memória automática por regras; não é um controle de histórico isolado.",
            "Na implementação atual, toda chamada a /conversas também processa as regras automáticas de memória.",
            "Memória persistente API é pré-carregada manualmente com o estado esperado do caso.",
            "O cenário memoria_regras_api processa mensagens anteriores pela API e mantém as memórias persistidas ao reiniciar a sessão antes da pergunta final.",
            "O cenário memoria_regras_api avalia a resposta final e a recuperação de memórias pela API; a correção do estado interno não é medida separadamente nesta execução.",
            "A limpeza remove os dados do usuário sintético ao terminar cada cenário.",
        ],
        "resultados": resultados,
        "resumo": resumir(resultados),
    }

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n===== RESUMO =====")
    for cenario, dados in documento["resumo"].items():
        taxa = dados["taxa_aprovacao_pct"]
        print(
            f"{cenario}: {dados['aprovados']}/{dados['executados']} acertos "
            f"({taxa if taxa is not None else 'n/d'}%) | "
            f"tokens={dados['tokens_total']} | "
            f"latência média/caso={dados['latencia_api_media_por_caso_ms']} ms"
        )

        if cenario in CENARIOS_MEMORIA:
            print(
                "  recuperação exata: "
                f"{dados['memorias_recuperadas_exatamente']}/"
                f"{dados['casos_com_memoria_esperada']}; "
                f"casos sem memória esperada sem resíduos: "
                f"{dados['casos_sem_residuos_memoria']}/"
                f"{dados['casos_sem_memoria_esperada']}"
            )

        if cenario == "memoria_regras_api":
            print(
                "  estados das regras corretos: "
                f"{dados['estados_regras_corretos']}/"
                f"{dados['estados_regras_verificados']}"
            )

    print(f"\nRelatório salvo em: {saida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())