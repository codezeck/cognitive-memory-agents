"""P6: orquestração independente com evidência JSONL incremental.

Sem anotações de resposta aprovadas, os julgamentos ficam não verificados.
O dataset de recuperação não é convertido automaticamente em gabarito do chatbot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from eval.avaliar_comparativo import (
    _tokens_comparaveis, avaliar_vazamento_esquecidos, resumir_metricas_resposta,
    tokens_etapa, validar_dataset_p4,
)
from eval.julgamento_respostas import julgar_resposta
from eval.sessoes_evidencias import VerificadorEvidencias
from eval.sessoes_transporte import (
    Credencial, Evento, TransporteHTTP, TransporteHistorico, mensagem_aprovada,
)

DATASET = ROOT_DIR / "eval/memoria/sessoes.json"
CENARIOS = ("memoria_automatica", "historico_completo")
MODELO_EVENTOS = {"fato", "pergunta", "esquecer_chaves"}


def cobertura_anotacoes(eventos, anotacoes):
    perguntas = {e.id: e for e in eventos if e.tipo == "pergunta"}
    if not isinstance(anotacoes, dict) or anotacoes.keys() - perguntas.keys():
        raise ValueError("Anotações devem referenciar perguntas existentes.")
    validas, detalhes = {}, {}
    for qid, evento in perguntas.items():
        if qid not in anotacoes:
            detalhes[qid] = {"estado": "ausente", "motivo": "dependência de anotação externa (Vinícius)"}
            continue
        anotacao = anotacoes[qid]
        try:
            if not isinstance(anotacao, dict):
                raise ValueError("Anotação deve ser objeto.")
            validar_dataset_p4([{**anotacao, "id": qid, "mensagens": [evento.texto]}])
        except ValueError as erro:
            detalhes[qid] = {"estado": "incompativel", "motivo": str(erro)}
        else:
            validas[qid] = anotacao
            detalhes[qid] = {"estado": "compativel"}
    return validas, {"perguntas_previstas": len(perguntas), "compativeis": len(validas),
                     "ausentes": sum(d["estado"] == "ausente" for d in detalhes.values()),
                     "incompativeis": sum(d["estado"] == "incompativel" for d in detalhes.values()),
                     "numerador": len(validas), "denominador": len(perguntas),
                     "cobertura_pct": round(100 * len(validas) / len(perguntas), 2),
                     "perguntas": detalhes}


def _medida(valores):
    """True/False: verificado; None: não verificado; 'nao_aplicavel': fora do escopo."""
    elegiveis = [v for v in valores if v != "nao_aplicavel"]
    verificados = [v for v in elegiveis if type(v) is bool]
    return {"tentativas_previstas": len(valores), "tentativas_elegiveis": len(elegiveis),
            "julgamentos_verificados": len(verificados), "numerador": sum(v is True for v in verificados),
            "denominador": len(verificados), "nao_verificados": len(elegiveis) - len(verificados),
            "nao_aplicaveis": len(valores) - len(elegiveis),
            "cobertura_pct": round(100 * len(verificados) / len(elegiveis), 2) if elegiveis else None,
            "taxa_pct": round(100 * sum(verificados) / len(verificados), 2) if verificados else None}


def avaliar_recuperacao(registro, referencia):
    """Indícios lexicais do contexto recuperado, separados da resposta e do esquecimento."""
    from src.memoria.benchmark import normalizar
    nomes = ("esperado_presente", "proibido_presente", "contexto_vazio_sem_esperado")
    if registro["cenario"] == "historico_completo":
        return dict.fromkeys(nomes, "nao_aplicavel")
    valores = registro.get("resultado", {}).get("memorias_usadas")
    conhecido = (registro.get("trajetoria_integra") is True and registro.get("estado") == "concluido"
                 and isinstance(valores, list) and all(isinstance(v, str) for v in valores))
    texto = normalizar("\n".join(valores)) if conhecido else None
    esperado, proibido = referencia["esperado"], referencia["proibido"]
    return {
        "esperado_presente": (all(normalizar(v) in texto for v in esperado) if conhecido else None)
        if esperado else "nao_aplicavel",
        "proibido_presente": (any(normalizar(v) in texto for v in proibido) if conhecido else None)
        if proibido else "nao_aplicavel",
        "contexto_vazio_sem_esperado": (not valores if conhecido else None)
        if not esperado else "nao_aplicavel",
    }


def planejar(dados: dict) -> tuple[Evento, ...]:
    """Intercala usuários por sessão; textos são cópias literais da fonte."""
    if not isinstance(dados, dict):
        raise ValueError("Dataset de sessões deve ser um objeto.")
    usuarios = dados.get("usuarios")
    if not isinstance(usuarios, list) or len(usuarios) != 4:
        raise ValueError("A P6 exige quatro usuários e cinco sessões por usuário.")
    ids = [u.get("usuario_id") for u in usuarios if isinstance(u, dict)]
    if (len(ids) != 4 or any(not isinstance(u, str) or not u.strip() for u in ids)
            or len(set(ids)) != 4):
        raise ValueError("Usuários precisam de identificadores distintos e não vazios.")
    for u in usuarios:
        sessoes = u.get("sessoes", [])
        if (not isinstance(sessoes, list) or len(sessoes) != 5
                or any(not isinstance(s, dict) or type(s.get("sessao")) is not int for s in sessoes)
                or {s["sessao"] for s in sessoes} != set(range(1, 6))):
            raise ValueError(f"{u['usuario_id']}: sessões devem ser exatamente 1 a 5.")
        if not isinstance(u.get("perguntas"), list):
            raise ValueError("Perguntas devem ser uma lista.")
        for q in u["perguntas"]:
            if (not isinstance(q, dict) or type(q.get("apos_sessao")) is not int
                    or q["apos_sessao"] not in range(1, 6)
                    or not isinstance(q.get("pergunta"), str) or not q["pergunta"].strip()
                    or any(not isinstance(q.get(c), list)
                           or any(not isinstance(t, str) or not t.strip() for t in q[c])
                           for c in ("esperado", "proibido"))):
                raise ValueError("Pergunta ou referências de recuperação inválidas.")
    if sum(len(u["perguntas"]) for u in usuarios) != 21:
        raise ValueError("A P6 exige as 21 perguntas do protocolo.")
    eventos = []
    for numero in range(1, 6):
        for usuario in usuarios:
            uid = usuario["usuario_id"]
            sessao = next(s for s in usuario["sessoes"] if s["sessao"] == numero)
            prefixo = f"{uid}/s{numero}"
            eventos.append(Evento(prefixo + "/iniciar", uid, numero, "iniciar_sessao"))
            apagar = sessao.get("apagar_usuario", False)
            if type(apagar) is not bool:
                raise ValueError("apagar_usuario deve ser booleano.")
            if apagar:
                eventos.extend([
                    Evento(prefixo + "/apagar_usuario", uid, numero, "apagar_usuario"),
                    Evento(prefixo + "/checkpoint_exclusao", uid, numero, "checkpoint_exclusao"),
                ])
            chaves = sessao.get("esquecer_chaves", [])
            if not isinstance(chaves, list) or any(not isinstance(c, str) or not c.strip() for c in chaves):
                raise ValueError("esquecer_chaves deve ser lista de chaves não vazias.")
            if chaves:
                eventos.extend([
                    Evento(prefixo + "/esquecer_chaves", uid, numero, "esquecer_chaves", chaves=tuple(chaves)),
                    Evento(prefixo + "/checkpoint_exclusao_chaves", uid, numero,
                           "checkpoint_exclusao", chaves=tuple(chaves)),
                ])
            fatos = sessao.get("fatos", [])
            if not isinstance(fatos, list):
                raise ValueError("fatos deve ser lista.")
            for indice, fato in enumerate(fatos, 1):
                if (not isinstance(fato, dict) or any(not isinstance(fato.get(c), str)
                        or not fato[c].strip() for c in ("texto", "chave"))):
                    raise ValueError("Fato precisa de texto e chave explícitos.")
                eventos.append(Evento(f"{prefixo}/fato{indice}", uid, numero, "fato",
                                      texto=fato["texto"], chaves=(fato["chave"],)))
            for indice, q in enumerate(usuario["perguntas"], 1):
                if q["apos_sessao"] == numero:
                    eventos.append(Evento(f"{prefixo}/pergunta{indice}", uid, numero,
                                          "pergunta", texto=q["pergunta"]))
            eventos.append(Evento(prefixo + "/checkpoint_persistencia", uid, numero,
                                  "checkpoint_persistencia"))
    return tuple(eventos)


def classificar_checkpoint(evento, resultado, *, cenario, simulado):
    if cenario == "historico_completo":
        return "nao_aplicavel"
    if not simulado and resultado.get("evidencia_status") != "compativel":
        return "nao_verificado"
    if evento.tipo == "checkpoint_persistencia":
        antes, depois = resultado.get("estado_antes"), resultado.get("estado_depois")
        verificado = (resultado.get("reinicio_confirmado") is True
                      and isinstance(antes, (dict, list)) and bool(antes) and antes == depois)
        completo = (type(resultado.get("reinicio_confirmado")) is bool
                    and isinstance(antes, (dict, list)) and bool(antes)
                    and isinstance(depois, type(antes)))
    else:
        completo = (all(type(resultado.get(c)) is int and resultado[c] >= 0
                        for c in ("alvos_ativos", "alvos_substituidos", "alvos_no_historico"))
                    and type(resultado.get("nao_alvos_preservados")) is bool)
        verificado = (all(type(resultado.get(c)) is int and resultado[c] == 0
                          for c in ("alvos_ativos", "alvos_substituidos", "alvos_no_historico"))
                      and resultado.get("nao_alvos_preservados") is True)
    if not verificado:
        return "reprovado" if completo else "nao_verificado"
    return "verificado_simulado" if simulado else "verificado"


def _tokens(registros):
    chamadas = [r.get("resultado", {}) for r in registros]
    medida = tokens_etapa(chamadas)
    medida["chamadas_previstas"] = len(registros)
    medida["chamadas_observadas"] = sum("resultado" in r for r in registros)
    if medida["chamadas_observadas"] < len(registros):
        medida["chamadas_modelo"] = None
    medida["cobertura"] = {
        canal: {"numerador": medida[f"chamadas_com_{canal}"], "denominador": len(registros),
                "nao_verificados": len(registros) - medida[f"chamadas_com_{canal}"],
                "cobertura_pct": round(100 * medida[f"chamadas_com_{canal}"] / len(registros), 2)
                if registros else None} for canal in ("entrada", "saida")
    }
    return medida


def _sessao(cenario, uid, numero, registros):
    chamadas = [r for r in registros if r["evento"]["tipo"] in MODELO_EVENTOS]
    latencias = [r.get("resultado", {}).get("latencia_ms") for r in chamadas]
    conhecidas = [v for v in latencias if type(v) in (int, float) and math.isfinite(v) and v >= 0]
    return {
        "tipo": "sessao", "cenario": cenario, "usuario_id": uid, "sessao": numero,
        "estado": "incompleta" if any(r["estado"] == "erro" for r in registros) else "concluida",
        "perguntas": sum(r["evento"]["tipo"] == "pergunta" for r in registros),
        "falhas": sum(r["estado"] == "erro" for r in registros),
        "configuracao_comparavel": not any(r.get("resultado", {}).get("configuracao_compativel") is False for r in chamadas),
        "tokens": {
            "ingestao": _tokens([r for r in chamadas if r["evento"]["tipo"] != "pergunta"]),
            "perguntas": _tokens([r for r in chamadas if r["evento"]["tipo"] == "pergunta"]),
            "sessao": _tokens(chamadas),
        },
        "latencia_chamadas_ms": sum(conhecidas) if len(conhecidas) == len(chamadas) else None,
        "latencia_observada_ms": sum(conhecidas) if conhecidas or not chamadas else None,
        "cobertura_latencia": {"numerador": len(conhecidas), "denominador": len(chamadas),
                               "cobertura_pct": round(100 * len(conhecidas) / len(chamadas), 2) if chamadas else None},
        "tempo_orquestracao_ms": round(sum(r["duracao_ms"] for r in registros), 2),
    }


def comparar_sessoes(sessoes):
    indices = {c: defaultdict(list) for c in CENARIOS}
    for sessao in sessoes:
        indices[sessao["cenario"]][(sessao["usuario_id"], sessao["sessao"])].append(sessao)
    pares = sorted(indices[CENARIOS[0]].keys() & indices[CENARIOS[1]].keys())
    unicos = [chave for chave in pares if all(len(indices[c][chave]) == 1 for c in CENARIOS)]
    comparacoes = {}
    for etapa in ("ingestao", "perguntas", "sessao"):
        comparacoes[etapa] = {}
        for campo in ("tokens_entrada", "tokens_saida", "tokens_total"):
            medidos = []
            for chave in unicos:
                if any(indices[c][chave][0].get("configuracao_comparavel") is False for c in CENARIOS):
                    continue
                automatico = indices["memoria_automatica"][chave][0]["tokens"][etapa]
                historico = indices["historico_completo"][chave][0]["tokens"][etapa]
                if all(_tokens_comparaveis(m, campo) for m in (automatico, historico)):
                    medidos.append((chave, automatico[campo], historico[campo]))
            auto = sum(p[1] for p in medidos) if medidos else None
            hist = sum(p[2] for p in medidos) if medidos else None
            comparacoes[etapa][campo] = {
                "pares_previstos": 20, "cobertura_pct": round(100 * len(medidos) / 20, 2),
                "pares_identificados": len(pares), "pares_medidos": len(medidos),
                "chaves_duplicadas_descartadas": len(pares) - len(unicos),
                "pares_sem_medicao": len(unicos) - len(medidos),
                "sessoes": [{"usuario_id": p[0][0], "sessao": p[0][1]} for p in medidos],
                "tokens_automaticos": auto, "tokens_historico": hist,
                "reducao_pct": round(100 * (1 - auto / hist), 2) if hist else None,
            }
    return comparacoes


def executar(dados, transportes, saida, *, provedor="ollama", modelo="qwen2.5-coder:3b",
             anotacoes=None, repeticao=1, execucao_id=None):
    eventos = planejar(dados)
    if (set(transportes) != set(CENARIOS) or len({id(t) for t in transportes.values()}) != 2
            or any(t.cenario != c or type(t.simulado) is not bool for c, t in transportes.items())
            or len({t.simulado for t in transportes.values()}) != 1):
        raise ValueError("Forneça dois transportes independentes, identificados e do mesmo modo real/simulado.")
    if type(repeticao) is not int or repeticao < 1:
        raise ValueError("Repetição deve ser inteiro positivo.")
    anotacoes = {} if anotacoes is None else anotacoes
    anotacoes_validas, cobertura = cobertura_anotacoes(eventos, anotacoes)
    execucao_id = uuid.uuid4().hex if execucao_id is None else execucao_id
    if not isinstance(execucao_id, str) or not execucao_id.strip():
        raise ValueError("Identificador de execução deve ser texto não vazio.")
    referencias = {f"{u['usuario_id']}/s{q['apos_sessao']}/pergunta{i}": q
                   for u in dados["usuarios"] for i, q in enumerate(u["perguntas"], 1)}
    for transporte in transportes.values():
        transporte.validar(eventos)
    contratos_registrados = {}
    if all(hasattr(t, "contratos") for t in transportes.values()):
        for evento in eventos:
            if evento.tipo == "esquecer_chaves":
                mensagens = {mensagem_aprovada(evento, t.contratos) for t in transportes.values()}
                if len(mensagens) != 1:
                    raise ValueError("Os cenários devem usar a mesma mensagem de ação aprovada.")
                contrato = next(iter(transportes.values())).contratos[evento.id]
                contratos_registrados[evento.id] = {
                    "mensagem": contrato["mensagem"], "referencia": contrato["referencia"],
                }

    sessoes, resultados, falhas_fechamento, falhas_inicio = [], [], [], []
    proveniencia = {}
    agrupados = defaultdict(list)
    integridade = defaultdict(lambda: True)
    simulado = next(iter(transportes.values())).simulado
    saida = Path(saida)
    with saida.open("x", encoding="utf-8") as arquivo:
        def registrar(item):
            arquivo.write(json.dumps(item, ensure_ascii=False, allow_nan=False) + "\n")
            arquivo.flush()

        try:
            commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True, stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            commit = None
        registrar({
            "tipo": "inicio", "versao": "p6-etapa2", "execucao_id": execucao_id,
            "gerado_em": datetime.now(timezone.utc).isoformat(), "simulado": simulado,
            "provedor": provedor, "modelo": modelo, "repeticao": repeticao,
            "commit": commit,
            "identificacao_transportes": {c: t.identificar() if callable(getattr(t, "identificar", None))
                                           else {"simulado": t.simulado} for c, t in transportes.items()},
            "contratos_acoes": contratos_registrados,
            "executor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "transporte_sha256": hashlib.sha256(Path(__file__).with_name("sessoes_transporte.py").read_bytes()).hexdigest(),
            "verificador_sha256": hashlib.sha256(Path(__file__).with_name("sessoes_evidencias.py").read_bytes()).hexdigest(),
            "dataset_sha256_canonico": hashlib.sha256(json.dumps(dados, ensure_ascii=True, sort_keys=True).encode()).hexdigest(),
            "anotacoes_sha256_canonico": hashlib.sha256(json.dumps(anotacoes, ensure_ascii=True, sort_keys=True).encode()).hexdigest(),
            "usuarios": 4, "sessoes_por_cenario": 20, "perguntas_por_cenario": 21,
            "cobertura_anotacoes": cobertura,
            "persistencia": "depende de evidência de reinício; nova sessão não é reinício",
        })
        try:
            # Barreira GLOBAL: os dois cenários só começam após verificar os quatro usuários.
            for cenario, transporte in transportes.items():
                registrar({"tipo": "tentativa_preflight", "cenario": cenario})
                try:
                    proveniencia[cenario] = transporte.verificar_inicio(
                        eventos, execucao_id=execucao_id, provedor=provedor, modelo=modelo,
                    )
                    registrar({"tipo": "preflight", "cenario": cenario,
                               "estado": "concluido", "proveniencia": proveniencia[cenario]})
                except Exception as erro:
                    falha = {"cenario": cenario, "tipo": type(erro).__name__, "mensagem": str(erro)[:500]}
                    falhas_inicio.append(falha)
                    registrar({"tipo": "preflight", "estado": "erro", **falha})
                    break
            for evento in eventos if not falhas_inicio else ():
                for cenario in CENARIOS:
                    transporte = transportes[cenario]
                    registrar({"tipo": "tentativa", "cenario": cenario, "evento": asdict(evento)})
                    inicio = time.perf_counter()
                    registro = {"tipo": "resultado", "cenario": cenario, "evento": asdict(evento)}
                    try:
                        resposta = transporte.executar(evento, provedor=provedor, modelo=modelo)
                        if not isinstance(resposta, dict):
                            raise ValueError("Transporte deve devolver objeto JSON.")
                        resposta = json.loads(json.dumps(resposta, allow_nan=False))
                        registro.update(estado="concluido", resultado=resposta)
                        if resposta.get("configuracao_compativel") is False:
                            integridade[(cenario, evento.usuario_id)] = False
                            registro.update(estado="erro", erro={"tipo": "ConfiguracaoIncompativel",
                                            "mensagem": "API retornou provedor/modelo diferente do solicitado."})
                        if evento.tipo.startswith("checkpoint_"):
                            registro["checkpoint"] = classificar_checkpoint(
                                evento, resposta, cenario=cenario, simulado=simulado,
                            )
                    except Exception as erro:
                        integridade[(cenario, evento.usuario_id)] = False
                        registro.update(estado="erro", erro={"tipo": type(erro).__name__, "mensagem": str(erro)[:500]})
                        if evento.tipo.startswith("checkpoint_"):
                            registro["checkpoint"] = "nao_verificado"
                    registro["duracao_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
                    registro["trajetoria_integra"] = integridade[(cenario, evento.usuario_id)]
                    if evento.tipo == "pergunta":
                        anotacao = anotacoes_validas.get(evento.id, {})
                        texto = registro.get("resultado", {}).get("resposta")
                        if registro["trajetoria_integra"]:
                            registro["julgamento"] = julgar_resposta(texto, anotacao)
                        else:
                            registro["julgamento_observado"] = julgar_resposta(texto, anotacao)
                            registro["julgamento"] = julgar_resposta(None, anotacao)
                        registro["anotacao_disponivel"] = evento.id in anotacoes_validas
                        registro["anotacao_estado"] = cobertura["perguntas"][evento.id]["estado"]
                        registro["recuperacao"] = avaliar_recuperacao(registro, referencias[evento.id])
                        if anotacao:
                            registro["vazamento_esquecidos"] = avaliar_vazamento_esquecidos(
                                anotacao, registro.get("julgamento_observado", registro["julgamento"]),
                            )
                    registrar(registro)
                    resultados.append(registro)
                    agrupados[(cenario, evento.usuario_id, evento.sessao)].append(registro)
                    if evento.tipo == "checkpoint_persistencia":
                        sessao = _sessao(cenario, evento.usuario_id, evento.sessao,
                                         agrupados[(cenario, evento.usuario_id, evento.sessao)])
                        sessoes.append(sessao)
                        registrar(sessao)
        except BaseException as erro:
            registrar({"tipo": "interrupcao", "erro": type(erro).__name__})
            raise
        finally:
            for cenario, transporte in transportes.items():
                try:
                    transporte.fechar()
                except Exception as erro:
                    falhas_fechamento.append({"cenario": cenario, "tipo": type(erro).__name__})
            if falhas_fechamento:
                registrar({"tipo": "falhas_fechamento", "falhas": falhas_fechamento})
        perguntas_previstas = [e for e in eventos if e.tipo == "pergunta"]
        por_pergunta = {(r["cenario"], r["evento"]["id"]): r for r in resultados
                        if r["evento"]["tipo"] == "pergunta"}
        respostas = {}
        for c in CENARIOS:
            respostas[c] = []
            for e in perguntas_previstas:
                anotacao = anotacoes_validas.get(e.id, {})
                julgamento = julgar_resposta(None, anotacao)
                respostas[c].append(por_pergunta.get((c, e.id), {
                    "julgamento": julgamento,
                    "vazamento_esquecidos": avaliar_vazamento_esquecidos(anotacao, julgamento),
                }))
        recuperacao = {c: {
            nome: _medida([por_pergunta.get((c, e.id), {}).get("recuperacao", {}).get(
                nome, avaliar_recuperacao({"cenario": c}, referencias[e.id])[nome])
                for e in perguntas_previstas])
            for nome in ("esperado_presente", "proibido_presente", "contexto_vazio_sem_esperado")
        } for c in CENARIOS}
        checkpoints = {c: {} for c in CENARIOS}
        for c in CENARIOS:
            for tipo in ("checkpoint_persistencia", "checkpoint_exclusao"):
                previstos = [e for e in eventos if e.tipo == tipo]
                estados = {r["evento"]["id"]: r.get("checkpoint") for r in resultados if r["cenario"] == c}
                checkpoints[c][tipo] = _medida([
                    "nao_aplicavel" if c == "historico_completo" else
                    True if estados.get(e.id) in {"verificado", "verificado_simulado"} else
                    False if estados.get(e.id) == "reprovado" else None
                    for e in previstos])
        resumo = {
            "tipo": "fim", "simulado": simulado, "sessoes": sessoes,
            "estado_orquestracao": "incompleta" if falhas_inicio or falhas_fechamento or any(
                r["estado"] == "erro" for r in resultados) else "concluida",
            "falhas": len(falhas_inicio) + sum(r["estado"] == "erro" for r in resultados),
            "falhas_inicio": falhas_inicio, "proveniencia": proveniencia,
            "cobertura_anotacoes": cobertura,
            "avaliacao_respostas_completa": cobertura["compativeis"] == 21 and all(
                len([r for r in resultados if r["cenario"] == c and r["evento"]["tipo"] == "pergunta"
                     and r["trajetoria_integra"] and not r["julgamento"]["revisao_necessaria"]]) == 21 for c in CENARIOS),
            "perguntas_previstas_por_cenario": 21,
            "perguntas_observadas": {c: sum(r["cenario"] == c and r["evento"]["tipo"] == "pergunta"
                                            for r in resultados) for c in CENARIOS},
            "metricas_recuperacao_lexical": recuperacao,
            "metricas_checkpoints": checkpoints,
            "falhas_fechamento": falhas_fechamento,
            "metricas_resposta": {c: resumir_metricas_resposta(respostas[c]) for c in CENARIOS},
            "comparacoes_tokens": comparar_sessoes(sessoes),
        }
        registrar(resumo)
    return {**resumo, "resultados": resultados}


def main():
    parser = argparse.ArgumentParser(description="Executor P6; não altera o dataset nem preenche anotações.")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--saida", type=Path)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--credenciais", type=Path)
    parser.add_argument("--contratos-acoes", type=Path)
    parser.add_argument("--anotacoes", type=Path)
    parser.add_argument("--evidencias", type=Path, help="Documento LOCAL aprovado; não é contrato HTTP.")
    parser.add_argument("--execucao-id", help="Identificador exclusivo compartilhado com as evidências externas.")
    parser.add_argument("--provedor", default="ollama")
    parser.add_argument("--modelo", default="qwen2.5-coder:3b")
    parser.add_argument("--timeout-historico", type=float)
    parser.add_argument("--executar", action="store_true", help="Sem este argumento, somente inspeciona o plano.")
    args = parser.parse_args()
    try:
        dados = json.loads(args.dataset.read_text(encoding="utf-8"))
        eventos = planejar(dados)
        if not args.executar:
            anotacoes = json.loads(args.anotacoes.read_text(encoding="utf-8")) if args.anotacoes else {}
            _, cobertura = cobertura_anotacoes(eventos, anotacoes)
            print(json.dumps({"usuarios": 4, "sessoes": 20, "perguntas": 21,
                              "cobertura_anotacoes": cobertura,
                              "acoes_que_exigem_contrato": [e.id for e in eventos if e.tipo == "esquecer_chaves"]}))
            return 0
        if not args.saida or not args.credenciais:
            parser.error("Execução exige --saida e --credenciais de usuários dedicados.")
        contratos = json.loads(args.contratos_acoes.read_text(encoding="utf-8")) if args.contratos_acoes else {}
        anotacoes = json.loads(args.anotacoes.read_text(encoding="utf-8")) if args.anotacoes else {}
        credenciais = {u: Credencial(**c) for u, c in json.loads(args.credenciais.read_text(encoding="utf-8")).items()}
        import httpx
        cliente = httpx.Client(base_url=args.base_url, timeout=120)
        transportes = {
            "memoria_automatica": TransporteHTTP(cliente, credenciais, contratos=contratos,
                                                verificar_checkpoint=VerificadorEvidencias(args.evidencias)),
            "historico_completo": TransporteHistorico(contratos=contratos, timeout=args.timeout_historico),
        }
        try:
            resumo = executar(dados, transportes, args.saida, provedor=args.provedor,
                              modelo=args.modelo, anotacoes=anotacoes, execucao_id=args.execucao_id)
        finally:
            cliente.close()
        return 1 if resumo["estado_orquestracao"] == "incompleta" else 0
    except (ValueError, OSError, TypeError) as erro:
        parser.error(str(erro))


if __name__ == "__main__":
    raise SystemExit(main())
