from __future__ import annotations

import argparse
import json
import math
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

from eval.historico_processo import executar_historico_em_processo
from eval.julgamento_respostas import (
    ATRIBUTOS, VERSAO as VERSAO_JULGADOR,
    caso_para_julgamento, julgar_resposta, resumir_julgamentos,
)
from src.api.agente_local import AgenteLocal
from src.api.catalogo import SelecaoModelo

USUARIO_ID = "eval_comparativo"
USUARIO_HISTORICO = f"{USUARIO_ID}_historico"
DATASET = ROOT_DIR / "eval" / "dataset_comparativo.json"
VERSAO_METRICAS_RESPOSTA = "p5-v1"

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

    avaliacao = caso.get("avaliacao", {})
    if isinstance(avaliacao, dict) and avaliacao.get("tipo_resposta") == "abstencao":
        return "DESCONHECIDO"
    # Compatibilidade de exibição dos casos legados, sem inferir o julgamento.
    if isinstance(esperado, list) and esperado == ["não sei"]:
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
    """Compatibilidade booleana: conteúdo correto e ausência de proibidos."""
    return julgar_resposta(resposta, caso)["passou"]

ETAPAS_TOKENS = ("ingestao", "pergunta_final", "sessao")
CAMPOS_TOKENS = ("tokens_entrada", "tokens_saida", "tokens_total")


def _contagem_conhecida(valor):
    return type(valor) is int and valor >= 0


def tokens_etapa(chamadas: list[dict] | None) -> dict:
    """None indica medição desconhecida; [] indica zero chamadas realizadas."""
    quantidade = None if chamadas is None else len(chamadas)
    dados = {"chamadas_modelo": quantidade}
    for canal in ("entrada", "saida"):
        campo = f"tokens_{canal}"
        valores = [c.get(campo) for c in chamadas or []]
        # Os adaptadores não expõem a origem de zeros em chamadas realizadas.
        # Sem chamadas, o zero da etapa é comprovado; nas demais, é desconhecido.
        conhecidos = [v for v in valores if _contagem_conhecida(v) and v > 0]
        dados[f"chamadas_com_{canal}_zero_nao_verificado"] = sum(
            _contagem_conhecida(v) and v == 0 for v in valores
        )
        dados[campo] = (
            sum(conhecidos)
            if quantidade is not None and len(conhecidos) == quantidade else None
        )
        dados[f"{campo}_observados"] = (
            sum(conhecidos) if conhecidos else (0 if quantidade == 0 else None)
        )
        dados[f"chamadas_com_{canal}"] = len(conhecidos)
    dados["metricas_completas"] = all(
        dados[c] is not None for c in CAMPOS_TOKENS[:2]
    )
    dados["tokens_total"] = (
        dados["tokens_entrada"] + dados["tokens_saida"]
        if dados["metricas_completas"] else None
    )
    parcelas = [dados[f"{c}_observados"] for c in CAMPOS_TOKENS[:2]
                if dados[f"{c}_observados"] is not None]
    dados["tokens_total_observados"] = sum(parcelas) if parcelas else None
    dados["chamadas_com_tokens_zero"] = sum(
        any(_contagem_conhecida(c.get(k)) and c[k] == 0
            for k in CAMPOS_TOKENS[:2]) for c in chamadas or []
    )
    return dados


def tokens_por_etapa(chamadas: list[dict] | None) -> dict:
    return {
        "ingestao": tokens_etapa(chamadas[:-1] if chamadas else None),
        "pergunta_final": tokens_etapa(chamadas[-1:] if chamadas else None),
        "sessao": tokens_etapa(chamadas if chamadas else None),
    }


def tokens_tentativa(caso: dict, cenario: str, chamadas: list[dict]) -> dict:
    """Conserva parcelas recebidas sem supor que chamadas faltantes custaram zero."""
    previstas = (len(caso["mensagens"])
                 if cenario in {"historico_completo", "memoria_regras_api"} else 1)
    etapas = tokens_por_etapa(chamadas + [{} for _ in range(previstas - len(chamadas))])
    quantidades = {
        "ingestao": (previstas - 1, min(len(chamadas), previstas - 1)),
        "pergunta_final": (1, int(len(chamadas) == previstas)),
        "sessao": (previstas, len(chamadas)),
    }
    for etapa, (esperadas, observadas) in quantidades.items():
        etapas[etapa]["chamadas_previstas"] = esperadas
        etapas[etapa]["chamadas_observadas"] = observadas
        if observadas < esperadas:
            etapas[etapa]["chamadas_modelo"] = None
    return etapas


def preparacao_cenario(cenario: str, caso: dict) -> dict:
    manual = cenario == "memoria_persistente_api"
    return {
        "tipo": "estado_ouro_pre_carregado" if manual else (
            "conversacional" if cenario in {"historico_completo", "memoria_regras_api"}
            else "sem_fatos_anteriores"
        ),
        "memorias_previstas": len(caso.get("memorias", [])) if manual else 0,
        "custo_obtencao_estado_ouro": "nao_medido" if manual else "nao_aplicavel",
        "custo_total_sistema_medido": False,
    }


def metricas(chamadas: list[dict]) -> dict:
    latencias = [int(c.get("latencia_ms") or 0) for c in chamadas]

    return {
        **tokens_etapa(chamadas),
        "latencia_api_total_ms": sum(latencias),
        "latencia_api_media_ms": round(mean(latencias), 2) if latencias else 0,
    }


def executar_historico(caso: dict, provedor: str, modelo: str) -> list[dict]:
    """Executa o controle pelo agente, sem extração ou busca de memórias."""
    agente = AgenteLocal()
    selecao = SelecaoModelo(provedor.lower(), modelo)
    chamadas = []

    try:
        agente.nova_sessao(USUARIO_HISTORICO)
        for mensagem in caso["mensagens"]:
            inicio = time.perf_counter()
            resultado = agente.responder(
                usuario_id=USUARIO_HISTORICO,
                mensagem=mensagem,
                memorias=[],
                selecao=selecao,
            )
            chamadas.append({
                "resposta": resultado.resposta,
                "memorias_usadas": [],
                "tokens_entrada": resultado.tokens_entrada,
                "tokens_saida": resultado.tokens_saida,
                "latencia_ms": int((time.perf_counter() - inicio) * 1000),
            })
        return chamadas
    finally:
        agente.nova_sessao(USUARIO_HISTORICO)


def avaliar_vazamento_esquecidos(caso: dict, julgamento: dict) -> dict:
    """Projeta as ocorrências P4 somente nos alvos esquecidos explícitos."""
    medida = {
        "aplicavel": True, "status": "nao_verificado", "vazou": None,
        "ocorrencias": [], "motivo": "anotacao_ou_julgamento_insuficiente",
    }
    if "informacoes_esquecidas" not in caso:
        if caso.get("categoria") == "esquecimento":
            return medida
        esquecidas = []
    else:
        esquecidas = caso["informacoes_esquecidas"]
    if not isinstance(esquecidas, list) or not all(
        isinstance(v, str) and v.strip() for v in esquecidas
    ):
        return medida
    if not esquecidas:
        return {**medida, "aplicavel": False, "status": "nao_aplicavel",
                "motivo": "sem_alvos_esquecidos_anotados"}

    alvos = set(esquecidas)
    avaliacao = caso.get("avaliacao", {})
    aliases = avaliacao.get("aliases_proibidos", {}) if isinstance(avaliacao, dict) else {}
    if isinstance(aliases, dict):
        for alvo in esquecidas:
            valores = aliases.get(alvo, [])
            if isinstance(valores, list) and all(isinstance(v, str) and v.strip() for v in valores):
                alvos.update(valores)
    ocorrencias = julgamento.get("ocorrencias_proibidas")
    if not isinstance(ocorrencias, list) or not all(isinstance(v, str) for v in ocorrencias):
        return medida
    encontradas = sorted(alvos.intersection(ocorrencias))
    if encontradas:
        return {**medida, "status": "verificado", "vazou": True,
                "ocorrencias": encontradas, "motivo": "alvo_esquecido_presente"}
    criterio = julgamento.get("sem_informacao_proibida", {})
    if (julgamento.get("proibicao_aplicavel") is True
            and criterio.get("status") in {"aprovado", "reprovado"}):
        return {**medida, "status": "verificado", "vazou": False,
                "motivo": "sem_ocorrencia_dos_alvos_esquecidos"}
    return medida


def resumir_metricas_resposta(registros: list[dict]) -> dict:
    """Taxas condicionais à verificação, sempre acompanhadas da cobertura."""
    medidas = {
        "recuperacao_factual": [], "abstencao_correta": [], "vazamento_esquecidos": [],
    }
    for registro in registros:
        julgamento = registro.get("julgamento", {})
        modo = julgamento.get("tipo_resposta")
        for nome, criterio, tipo in (
            ("recuperacao_factual", "acerto_factual", "factual"),
            ("abstencao_correta", "abstencao_correta", "abstencao"),
        ):
            aplicavel = modo == tipo if modo in ("factual", "abstencao") else None
            decisao = julgamento.get(criterio, {})
            valor = (True if decisao.get("status") == "aprovado" and decisao.get("valor") is True
                     else False if decisao.get("status") == "reprovado" and decisao.get("valor") is False
                     else None)
            medidas[nome].append((aplicavel, valor))
        esquecimento = registro.get("vazamento_esquecidos", {})
        valor = esquecimento.get("vazou") if esquecimento.get("status") == "verificado" else None
        medidas["vazamento_esquecidos"].append((esquecimento.get("aplicavel"), valor))

    resumo = {}
    for nome, valores in medidas.items():
        elegiveis = [v for aplicavel, v in valores if aplicavel is True]
        verificados = [v for v in elegiveis if type(v) is bool]
        numerador = sum(v is True for v in verificados)
        resumo[nome] = {
            "tentativas_elegiveis": len(elegiveis),
            "julgamentos_verificados": len(verificados),
            "numerador": numerador, "denominador": len(verificados),
            "nao_verificados": len(elegiveis) - len(verificados),
            "nao_aplicaveis": sum(a is False for a, _ in valores),
            "aplicabilidade_desconhecida": sum(a is not True and a is not False for a, _ in valores),
            "cobertura_pct": round(100 * len(verificados) / len(elegiveis), 2) if elegiveis else None,
            "taxa_pct": round(100 * numerador / len(verificados), 2) if verificados else None,
        }
    return resumo


def executar_cenario(
    cliente: httpx.Client,
    caso: dict,
    cenario: str,
    provedor: str,
    modelo: str,
    *,
    timeout_historico: float | None = None,
    observacao_tokens: dict | None = None,
) -> dict:
    inicio = time.perf_counter()
    chamadas = []
    estado_regras = None
    estado_regras_ok = None
    memorias_esperadas = caso.get("memorias", [])
    esperado_cenario = resposta_esperada_cenario(caso, cenario)

    try:
        if cenario != "historico_completo":
            limpar_usuario(cliente)

        if cenario == "sem_memoria":
            # Não envia fatos anteriores nem mantém histórico entre casos.
            chamadas.append(
                conversar(cliente, caso["mensagens"][-1], provedor, modelo)
            )

        elif cenario == "historico_completo":
            chamadas = executar_historico_em_processo(
                caso, provedor, modelo, timeout=timeout_historico,
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

        caso_avaliacao = caso_para_julgamento(caso, cenario)
        julgamento = julgar_resposta(final["resposta"], caso_avaliacao)

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
            "via": "agente_local" if cenario == "historico_completo" else "api",
            "provedor": provedor.lower(),
            "modelo": modelo,
            "repeticao": None,
            "passou": julgamento["passou"],
            "julgamento": julgamento,
            "vazamento_esquecidos": avaliar_vazamento_esquecidos(caso, julgamento),
            "protocolo_ok": julgamento["protocolo_ok"],
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
            "tokens_por_etapa": tokens_por_etapa(chamadas),
            "preparacao": preparacao_cenario(cenario, caso),
        }
        return registro

    except Exception:
        if observacao_tokens is not None:
            observacao_tokens.update(tokens_tentativa(caso, cenario, chamadas))
        raise
    finally:
        # O filho reutiliza a limpeza local de executar_historico (P1).
        if cenario != "historico_completo":
            try:
                limpar_usuario(cliente)
            except Exception as erro:
                print(f"AVISO: não foi possível limpar o usuário sintético: {erro}")



def _resumir_tokens(grupo: list[dict], etapa: str) -> dict:
    # Resultados antigos só permitem recuperar o total da sessão, não suas fases.
    medidas = [r.get("tokens_por_etapa", {}).get(
        etapa, r if etapa == "sessao" else {}
    ) for r in grupo]
    dados = {"casos_tentados": len(grupo)}
    for campo in CAMPOS_TOKENS:
        conhecidos = [m.get(campo) for m in medidas
                      if _contagem_conhecida(m.get(campo))]
        observados = [m.get(f"{campo}_observados", m.get(campo)) for m in medidas]
        observados = [v for v in observados if _contagem_conhecida(v)]
        dados[campo] = (
            sum(conhecidos) if grupo and len(conhecidos) == len(grupo) else None
        )
        dados[f"{campo}_observados"] = sum(observados) if observados else None
        dados[f"casos_com_{campo}"] = len(conhecidos)
    medidos = dados["casos_com_tokens_total"]
    dados["casos_medidos"] = medidos
    dados["casos_desconhecidos"] = len(grupo) - medidos
    totais = [m["tokens_total"] for m in medidas
              if _contagem_conhecida(m.get("tokens_total"))]
    dados["media_tokens_total_por_caso_medido"] = (
        round(sum(totais) / medidos, 2) if medidos else None
    )
    dados["casos_com_tokens_zero"] = sum(
        m.get("chamadas_com_tokens_zero", 0) > 0 for m in medidas
    )
    return dados


def _tokens_comparaveis(medida: dict, campo: str) -> bool:
    valor = medida.get(campo)
    if not _contagem_conhecida(valor):
        return False
    if valor == 0:
        return (type(medida.get("chamadas_modelo")) is int
                and medida["chamadas_modelo"] == 0
                and medida.get("metricas_completas") is True)
    # Protege também a leitura de resultados anteriores à quarentena de zeros.
    if campo == "tokens_total":
        return not medida.get("chamadas_com_tokens_zero", 0)
    canal = campo.removeprefix("tokens_")
    return not medida.get(
        f"chamadas_com_{canal}_zero_nao_verificado",
        medida.get("chamadas_com_tokens_zero", 0),
    )


def comparar_tokens(resultados: list[dict]) -> dict:
    """Compara pares únicos de caso/repetição/provedor/modelo, por etapa e canal."""
    indices = {c: {} for c in CENARIOS}
    for r in resultados:
        chave = (r.get("id"), r.get("repeticao"), r.get("provedor"), r.get("modelo"))
        if (r.get("cenario") not in indices or type(chave[1]) is not int
                or chave[1] < 1 or not all(isinstance(v, str) and v for v in
                                          (chave[0], chave[2], chave[3]))):
            continue
        indices[r["cenario"]].setdefault(chave, []).append(r)

    historico = indices["historico_completo"]
    comparacoes = {}
    for cenario in CENARIOS:
        if cenario == "historico_completo":
            continue
        candidato = indices[cenario]
        comuns = sorted(historico.keys() & candidato.keys())
        unicos = [k for k in comuns if len(historico[k]) == len(candidato[k]) == 1]
        etapas = ETAPAS_TOKENS if cenario == "memoria_regras_api" else ("pergunta_final",)
        comparacoes[cenario] = {}
        for etapa in etapas:
            comparacoes[cenario][etapa] = {}
            for campo in CAMPOS_TOKENS:
                pares = []
                for chave in unicos:
                    registros = (historico[chave][0], candidato[chave][0])
                    medidas = [r.get("tokens_por_etapa", {}).get(etapa, {})
                               for r in registros]
                    if all(_tokens_comparaveis(m, campo) for m in medidas):
                        pares.append((chave, *(m[campo] for m in medidas)))
                base = sum(p[1] for p in pares) if pares else None
                valor = sum(p[2] for p in pares) if pares else None
                comparacoes[cenario][etapa][campo] = {
                    "pares_identificados": len(comuns),
                    "chaves_duplicadas_descartadas": len(comuns) - len(unicos),
                    "pares_medidos": len(pares),
                    "pares_sem_medicao": len(unicos) - len(pares),
                    "casos_repeticoes": [
                        {"id": p[0][0], "repeticao": p[0][1],
                         "provedor": p[0][2], "modelo": p[0][3]} for p in pares
                    ],
                    "tokens_historico": base,
                    "tokens_cenario": valor,
                    "reducao_pct": round(100 * (1 - valor / base), 2) if base else None,
                }
    return comparacoes


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
        tokens = {etapa: _resumir_tokens(grupo, etapa) for etapa in ETAPAS_TOKENS}
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
            "tokens_entrada": tokens["sessao"]["tokens_entrada"],
            "tokens_saida": tokens["sessao"]["tokens_saida"],
            "tokens_total": tokens["sessao"]["tokens_total"],
            "tokens_por_etapa": tokens,
            "julgamento": resumir_julgamentos(grupo),
            "metricas_resposta": resumir_metricas_resposta(grupo),
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




def validar_dataset_p4(casos) -> None:
    """Valida anotações explícitas, sem inferir fatos ou alterar o dataset."""
    if not isinstance(casos, list) or not casos:
        raise ValueError("o dataset deve ser uma lista não vazia de casos")

    def textos(valor):
        return isinstance(valor, list) and all(
            isinstance(v, str) and v.strip() for v in valor
        )

    erros = []
    ids = set()
    for indice, caso in enumerate(casos, 1):
        if not isinstance(caso, dict):
            erros.append(f"caso {indice}: deve ser um objeto")
            continue
        identificador = caso.get("id")
        nome = identificador if isinstance(identificador, str) and identificador.strip() else f"caso {indice}"
        if not isinstance(identificador, str) or not identificador.strip():
            erros.append(f"{nome}: id obrigatório")
        elif identificador in ids:
            erros.append(f"{nome}: id duplicado")
        else:
            ids.add(identificador)
        if not textos(caso.get("mensagens")) or not caso.get("mensagens"):
            erros.append(f"{nome}: mensagens deve conter textos não vazios")
        if not isinstance(caso.get("categoria"), str) or not caso["categoria"].strip():
            erros.append(f"{nome}: categoria obrigatória")
        avaliacao = caso.get("avaliacao")
        if not isinstance(avaliacao, dict):
            erros.append(f"{nome}: avaliacao ausente ou inválida; informe os metadados P4 explícitos")
            continue
        modo = avaliacao.get("tipo_resposta")
        atributo = avaliacao.get("atributo")
        if not isinstance(modo, str) or modo not in {"factual", "abstencao"}:
            erros.append(f"{nome}: avaliacao.tipo_resposta deve ser factual ou abstencao")
        if not isinstance(atributo, str) or atributo not in ATRIBUTOS:
            erros.append(f"{nome}: avaliacao.atributo ausente ou não suportado pelo julgador")
        if not textos(avaliacao.get("informacoes_proibidas")):
            erros.append(f"{nome}: avaliacao.informacoes_proibidas deve ser lista explícita (pode ser vazia)")
        if not textos(caso.get("informacoes_esquecidas", [])):
            erros.append(f"{nome}: informacoes_esquecidas inválidas")
        aliases = avaliacao.get("aliases_proibidos", {})
        if not isinstance(aliases, dict) or not all(
            isinstance(k, str) and k.strip() and textos(v) for k, v in aliases.items()
        ):
            erros.append(f"{nome}: avaliacao.aliases_proibidos inválidos")
        esperado = caso.get("esperado")
        if modo == "factual":
            if not isinstance(esperado, str) or not esperado.strip():
                erros.append(f"{nome}: esperado factual deve ser texto não vazio")
            for campo in ("aliases_aceitos", "valores_antigos"):
                if not textos(avaliacao.get(campo, [])):
                    erros.append(f"{nome}: avaliacao.{campo} inválidos")
        elif not ((isinstance(esperado, str) and esperado.strip())
                  or (textos(esperado) and esperado)):
            erros.append(f"{nome}: esperado ausente ou inválido")
    if erros:
        raise ValueError("; ".join(erros))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compara quatro estratégias de memória pela API autenticada."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--provedor", default="ollama")
    parser.add_argument("--modelo", default="qwen2.5-coder:3b")
    parser.add_argument("--repeticoes", type=int, default=1)
    parser.add_argument(
        "--timeout-historico", type=float, default=None,
        help="Prazo total em segundos por caso de histórico (padrão: 30 + 60 por turno).",
    )
    parser.add_argument(
        "--dataset",
        default="eval/dataset_comparativo.json",
        help="Arquivo JSON com os casos (padrão: conjunto de desenvolvimento).",
    )
    parser.add_argument(
        "--saida",
        default="eval/results_comparativo_api.json",
        help="Arquivo novo de saída; não sobrescreve resultados existentes.",
    )
    args = parser.parse_args()

    if args.repeticoes < 1:
        parser.error("--repeticoes precisa ser pelo menos 1.")
    if args.timeout_historico is not None and (
        not math.isfinite(args.timeout_historico) or args.timeout_historico <= 0
    ):
        parser.error("--timeout-historico precisa ser positivo e finito.")

    saida = Path(args.saida)
    if not saida.is_absolute():
        saida = ROOT_DIR / saida
    if saida.exists():
        raise SystemExit(
            f"O arquivo {saida} já existe. Escolha outro caminho com --saida."
        )

    dataset = Path(args.dataset)
    if not dataset.is_absolute():
        dataset = ROOT_DIR / dataset
    dataset = dataset.resolve()
    try:
        casos = json.loads(dataset.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as erro:
        parser.error(f"Não foi possível ler o dataset {dataset}: {erro}")
    try:
        validar_dataset_p4(casos)
    except ValueError as erro:
        parser.error(
            f"Dataset incompatível com P4: {erro}. "
            "Revise os metadados antes de executar a avaliação; nenhuma chamada à API ou ao modelo foi iniciada."
        )
    try:
        dataset_relatorio = str(dataset.relative_to(ROOT_DIR))
    except ValueError:
        dataset_relatorio = str(dataset)
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
                    observacao_tokens = {}
                    try:
                        registro = executar_cenario(
                            cliente,
                            caso,
                            cenario,
                            args.provedor,
                            args.modelo,
                            timeout_historico=args.timeout_historico,
                            observacao_tokens=observacao_tokens,
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
                            f"Tokens: {registro['tokens_total'] if registro['tokens_total'] is not None else 'desconhecido'} | "
                            f"latência API: {registro['latencia_api_total_ms']} ms"
                        )
                    except Exception as erro:
                        etapas = observacao_tokens or tokens_tentativa(caso, cenario, [])
                        julgamento = julgar_resposta(None, caso_para_julgamento(caso, cenario))
                        registro = {
                            "id": caso["id"],
                            "categoria": caso["categoria"],
                            "cenario": cenario,
                            "repeticao": repeticao,
                            "passou": False,
                            "erro": str(erro)[:500],
                            "julgamento": julgamento,
                            "vazamento_esquecidos": avaliar_vazamento_esquecidos(caso, julgamento),
                            "protocolo_ok": False,
                            "provedor": args.provedor.lower(),
                            "modelo": args.modelo,
                            **etapas["sessao"],
                            "tokens_por_etapa": etapas,
                            "preparacao": preparacao_cenario(cenario, caso),
                        }
                        print(f"ERRO: {erro}")

                    resultados.append(registro)

    documento = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "dataset": dataset_relatorio,
        "usuario_sintetico": USUARIO_ID,
        "versao_julgador": VERSAO_JULGADOR,
        "versao_metricas_resposta": VERSAO_METRICAS_RESPOSTA,
        "observacoes": [
            "Sem memória envia apenas a pergunta final.",
            "historico_completo usa AgenteLocal.responder com memorias=[], sem /conversas, extração ou busca de memórias; limpa o histórico local antes e depois de cada caso, inclusive em erro.",
            "Cada caso de historico_completo executa em processo spawn independente; o limite de histórico é ampliado apenas no filho para preservar todos os turnos do caso.",
            f"Timeout do histórico: {args.timeout_historico if args.timeout_historico is not None else 'automático: 30 + 60 segundos por turno'}; a supervisão encerra o filho em erro ou timeout.",
            "memoria_regras_api envia mensagens anteriores pela API, reinicia a sessão antes da pergunta final e preserva as memórias persistidas.",
            "Os cenários via API continuam processando as regras automáticas de memória em toda chamada a /conversas.",
            "No histórico local, os campos legados de latência medem a chamada direta ao agente, sem o percurso HTTP da API; essas latências não são equivalentes.",
            "Memória persistente API é pré-carregada manualmente com o estado esperado do caso.",
            "Tokens são separados em ingestão conversacional, pergunta final e sessão; entrada, saída e total são reportados independentemente quando conhecidos.",
            "Valores null são desconhecidos. Subtotais observados não representam custos completos; falhas e timeouts podem ter consumido tokens não recuperáveis pela P1/P2.",
            "Parcelas já recebidas pelo avaliador são preservadas mesmo em erro; chamadas não devolvidas pelo filho continuam desconhecidas.",
            "A preparação do estado-ouro, embeddings, regras, armazenamento e infraestrutura não têm seu custo medido em tokens de geração; zero chamadas de ingestão não significa preparação gratuita.",
            "Comparações usam pares únicos de caso, repetição, provedor e modelo; pré-carregada e sem memória são controles comparados apenas na pergunta final.",
            "Zeros reportados em chamadas são sinalizados e tratados como desconhecidos, sem economia calculada; zero de ingestão só é conhecido quando não houve chamadas nessa etapa.",
            "O cenário memoria_regras_api processa mensagens anteriores pela API e mantém as memórias persistidas ao reiniciar a sessão antes da pergunta final.",
            "O cenário memoria_regras_api avalia a resposta final e a recuperação de memórias pela API; a correção do estado interno não é medida separadamente nesta execução.",
            "A limpeza remove os dados do usuário sintético ao terminar cada cenário.",
            "P5 separa recuperação factual da resposta, abstenção e vazamento de alvos esquecidos explícitos; taxas usam julgamentos verificados, com cobertura e não verificados reportados à parte.",
            "Ausência de vazamento nos controles sem fatos anteriores ou com estado-ouro não comprova aquisição e esquecimento; ocorrências na resposta não medem exclusão completa no armazenamento.",
        ],
        "resultados": resultados,
        "resumo": resumir(resultados),
        "comparacoes_tokens": comparar_tokens(resultados),
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
            f"{cenario}: {dados['aprovados']}/{dados['casos']} acertos "
            f"({taxa if taxa is not None else 'n/d'}%) | "
            f"execuções concluídas={dados['executados']}; falhas={dados['falhas']} | "
            f"tokens={dados['tokens_total'] if dados['tokens_total'] is not None else 'desconhecido'} | "
            f"latência média/caso={dados['latencia_api_media_por_caso_ms']} ms"
        )

        for nome, medida in dados["metricas_resposta"].items():
            taxa_metrica = medida["taxa_pct"]
            cobertura = medida["cobertura_pct"]
            print(
                f"  {nome}: {medida['numerador']}/{medida['denominador']} verificados "
                f"(taxa={str(taxa_metrica) + '%' if taxa_metrica is not None else 'n/d'}) | "
                f"elegíveis={medida['tentativas_elegiveis']}; "
                f"cobertura={medida['julgamentos_verificados']}/{medida['tentativas_elegiveis']} "
                f"({str(cobertura) + '%' if cobertura is not None else 'n/d'}); "
                f"não verificados={medida['nao_verificados']}; "
                f"não aplicáveis={medida['nao_aplicaveis']}; "
                f"aplicabilidade desconhecida={medida['aplicabilidade_desconhecida']}"
            )

        for etapa, medida in dados["tokens_por_etapa"].items():
            canais = ", ".join(
                f"{c}={medida[c] if medida[c] is not None else 'desconhecido'}"
                for c in CAMPOS_TOKENS
            )
            print(f"  {etapa}: {canais}; casos medidos="
                  f"{medida['casos_medidos']}/{medida['casos_tentados']}")

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
