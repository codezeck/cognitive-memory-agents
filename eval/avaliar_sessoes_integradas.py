"""P6, etapa 1: orquestração independente com evidência JSONL incremental.

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
from eval.sessoes_transporte import (
    Credencial, Evento, TransporteHTTP, TransporteHistorico, mensagem_aprovada,
)

DATASET = ROOT_DIR / "eval/memoria/sessoes.json"
CENARIOS = ("memoria_automatica", "historico_completo")
MODELO_EVENTOS = {"fato", "pergunta", "esquecer_chaves"}


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
    if evento.tipo == "checkpoint_persistencia":
        antes, depois = resultado.get("estado_antes"), resultado.get("estado_depois")
        verificado = (resultado.get("reinicio_confirmado") is True
                      and isinstance(antes, (dict, list)) and bool(antes) and antes == depois)
    else:
        verificado = (all(type(resultado.get(c)) is int and resultado[c] == 0
                          for c in ("alvos_ativos", "alvos_substituidos", "alvos_no_historico"))
                      and resultado.get("nao_alvos_preservados") is True)
    if not verificado:
        return "nao_verificado"
    return "verificado_simulado" if simulado else "verificado"


def _tokens(registros):
    chamadas = [r.get("resultado", {}) if r["estado"] == "concluido" else {} for r in registros]
    medida = tokens_etapa(chamadas)
    medida["chamadas_previstas"] = len(registros)
    medida["chamadas_observadas"] = sum(r["estado"] == "concluido" for r in registros)
    if medida["chamadas_observadas"] < len(registros):
        medida["chamadas_modelo"] = None
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
        "tokens": {
            "ingestao": _tokens([r for r in chamadas if r["evento"]["tipo"] != "pergunta"]),
            "perguntas": _tokens([r for r in chamadas if r["evento"]["tipo"] == "pergunta"]),
            "sessao": _tokens(chamadas),
        },
        "latencia_chamadas_ms": sum(conhecidas) if len(conhecidas) == len(chamadas) else None,
        "latencia_observada_ms": sum(conhecidas) if conhecidas or not chamadas else None,
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
                automatico = indices["memoria_automatica"][chave][0]["tokens"][etapa]
                historico = indices["historico_completo"][chave][0]["tokens"][etapa]
                if all(_tokens_comparaveis(m, campo) for m in (automatico, historico)):
                    medidos.append((chave, automatico[campo], historico[campo]))
            auto = sum(p[1] for p in medidos) if medidos else None
            hist = sum(p[2] for p in medidos) if medidos else None
            comparacoes[etapa][campo] = {
                "pares_identificados": len(pares), "pares_medidos": len(medidos),
                "chaves_duplicadas_descartadas": len(pares) - len(unicos),
                "pares_sem_medicao": len(unicos) - len(medidos),
                "sessoes": [{"usuario_id": p[0][0], "sessao": p[0][1]} for p in medidos],
                "tokens_automaticos": auto, "tokens_historico": hist,
                "reducao_pct": round(100 * (1 - auto / hist), 2) if hist else None,
            }
    return comparacoes


def executar(dados, transportes, saida, *, provedor="ollama", modelo="qwen2.5-coder:3b",
             anotacoes=None, repeticao=1):
    eventos = planejar(dados)
    if (set(transportes) != set(CENARIOS) or len({id(t) for t in transportes.values()}) != 2
            or any(t.cenario != c or type(t.simulado) is not bool for c, t in transportes.items())
            or len({t.simulado for t in transportes.values()}) != 1):
        raise ValueError("Forneça dois transportes independentes, identificados e do mesmo modo real/simulado.")
    if type(repeticao) is not int or repeticao < 1:
        raise ValueError("Repetição deve ser inteiro positivo.")
    anotacoes = {} if anotacoes is None else anotacoes
    perguntas = {e.id for e in eventos if e.tipo == "pergunta"}
    if not isinstance(anotacoes, dict) or anotacoes.keys() - perguntas:
        raise ValueError("Anotações devem referenciar perguntas existentes.")
    for qid, anotacao in anotacoes.items():
        validar_dataset_p4([{**anotacao, "id": qid, "mensagens": [next(e.texto for e in eventos if e.id == qid)]}])
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

    sessoes, resultados, falhas_fechamento = [], [], []
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
            "tipo": "inicio", "versao": "p6-etapa1", "execucao_id": uuid.uuid4().hex,
            "gerado_em": datetime.now(timezone.utc).isoformat(), "simulado": simulado,
            "provedor": provedor, "modelo": modelo, "repeticao": repeticao,
            "commit": commit,
            "contratos_acoes": contratos_registrados,
            "executor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "transporte_sha256": hashlib.sha256(Path(__file__).with_name("sessoes_transporte.py").read_bytes()).hexdigest(),
            "dataset_sha256_canonico": hashlib.sha256(json.dumps(dados, ensure_ascii=True, sort_keys=True).encode()).hexdigest(),
            "anotacoes_sha256_canonico": hashlib.sha256(json.dumps(anotacoes, ensure_ascii=True, sort_keys=True).encode()).hexdigest(),
            "usuarios": 4, "sessoes_por_cenario": 20, "perguntas_por_cenario": 21,
            "persistencia": "depende de evidência de reinício; nova sessão não é reinício",
        })
        try:
            for evento in eventos:
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
                        anotacao = anotacoes.get(evento.id, {})
                        texto = registro.get("resultado", {}).get("resposta")
                        if registro["trajetoria_integra"]:
                            registro["julgamento"] = julgar_resposta(texto, anotacao)
                        else:
                            registro["julgamento_observado"] = julgar_resposta(texto, anotacao)
                            registro["julgamento"] = julgar_resposta(None, anotacao)
                        registro["anotacao_disponivel"] = evento.id in anotacoes
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
        resumo = {
            "tipo": "fim", "simulado": simulado, "sessoes": sessoes,
            "estado_orquestracao": "incompleta" if falhas_fechamento or any(
                r["estado"] == "erro" for r in resultados) else "concluida",
            "falhas": sum(r["estado"] == "erro" for r in resultados),
            "falhas_fechamento": falhas_fechamento,
            "metricas_resposta": {c: resumir_metricas_resposta([
                r for r in resultados if r["cenario"] == c and r["evento"]["tipo"] == "pergunta"
            ]) for c in CENARIOS},
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
    parser.add_argument("--provedor", default="ollama")
    parser.add_argument("--modelo", default="qwen2.5-coder:3b")
    parser.add_argument("--timeout-historico", type=float)
    parser.add_argument("--executar", action="store_true", help="Sem este argumento, somente inspeciona o plano.")
    args = parser.parse_args()
    try:
        dados = json.loads(args.dataset.read_text(encoding="utf-8"))
        eventos = planejar(dados)
        if not args.executar:
            print(json.dumps({"usuarios": 4, "sessoes": 20, "perguntas": 21,
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
            "memoria_automatica": TransporteHTTP(cliente, credenciais, contratos=contratos),
            "historico_completo": TransporteHistorico(contratos=contratos, timeout=args.timeout_historico),
        }
        try:
            executar(dados, transportes, args.saida, provedor=args.provedor,
                     modelo=args.modelo, anotacoes=anotacoes)
        finally:
            cliente.close()
        return 0
    except (ValueError, OSError, TypeError) as erro:
        parser.error(str(erro))


if __name__ == "__main__":
    raise SystemExit(main())
