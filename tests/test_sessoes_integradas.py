import copy
import json
from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from eval import avaliar_sessoes_integradas as integrado
from eval.sessoes_evidencias import VerificadorEvidencias
from eval.sessoes_transporte import (
    Credencial, Evento, TransporteHTTP, TransporteHistorico, mensagem_aprovada,
)

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def dados():
    return json.loads((RAIZ / "eval/memoria/sessoes.json").read_text(encoding="utf-8"))


class ClienteFalso:
    simulado = True

    def __init__(self, cenario, *, falhar=None, interromper=None, observar=None):
        self.cenario = cenario
        self.falhar, self.interromper, self.observar = falhar, interromper, observar
        self.eventos = []
        self.historicos = defaultdict(list)
        self.memorias = defaultdict(dict)
        self.substituidas = defaultdict(lambda: defaultdict(list))
        self.maior_historico = defaultdict(int)
        self.fechar_chamadas = 0

    def validar(self, eventos):
        self.plano = eventos

    def verificar_inicio(self, eventos, **kwargs):
        return {"simulado": True, "usuarios": sorted({e.usuario_id for e in eventos})}

    def executar(self, e, *, provedor, modelo):
        if self.observar:
            self.observar(e)
        if e.id == self.interromper:
            raise KeyboardInterrupt()
        if e.id == self.falhar:
            raise TimeoutError("falha simulada")
        self.eventos.append(e)
        uid = e.usuario_id
        automatico = self.cenario == "memoria_automatica"
        if e.tipo == "iniciar_sessao":
            if automatico:
                self.historicos[uid].clear()
        elif e.tipo in {"fato", "pergunta", "esquecer_chaves"}:
            if e.tipo == "fato" and automatico:
                chave = e.chaves[0]
                if chave in self.memorias[uid]:
                    self.substituidas[uid][chave].append(self.memorias[uid][chave])
                self.memorias[uid][chave] = e.texto
            if e.tipo == "esquecer_chaves" and automatico:
                for chave in e.chaves:
                    self.memorias[uid].pop(chave, None)
                    self.substituidas[uid].pop(chave, None)
                self.historicos[uid].clear()
            else:
                self.historicos[uid].append(e.texto)
            self.maior_historico[uid] = max(self.maior_historico[uid], len(self.historicos[uid]))
            return {"resposta": "resposta simulada", "tokens_entrada": 10,
                    "tokens_saida": 2, "latencia_ms": 1, "memorias_usadas": []}
        elif e.tipo == "apagar_usuario":
            self.memorias[uid].clear()
            self.substituidas[uid].clear()
            self.historicos[uid].clear()
        elif e.tipo == "checkpoint_persistencia":
            estado = copy.deepcopy(self.memorias[uid])
            return {"reinicio_confirmado": True, "estado_antes": estado,
                    "estado_depois": copy.deepcopy(estado)}
        elif e.tipo == "checkpoint_exclusao":
            return {"alvos_ativos": sum(k in self.memorias[uid] for k in e.chaves) if e.chaves else len(self.memorias[uid]),
                    "alvos_substituidos": sum(len(self.substituidas[uid].get(k, [])) for k in e.chaves)
                    if e.chaves else sum(map(len, self.substituidas[uid].values())),
                    "alvos_no_historico": len(self.historicos[uid]),
                    "nao_alvos_preservados": True}
        return {}

    def fechar(self):
        self.fechar_chamadas += 1


def clientes(**kwargs):
    return {c: ClienteFalso(c, **kwargs) for c in integrado.CENARIOS}


def ler_log(caminho):
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()]


def contrato_fixture(eventos):
    # Mensagem já existente nos testes do repositório. Aprovação fictícia só para transporte simulado.
    return {e.id: {"mensagem": "Esqueça meu carro.", "aprovado": True,
                   "referencia": "fixture-simulada-nao-e-aprovacao-do-dataset"}
            for e in eventos if e.tipo == "esquecer_chaves"}


def documento_fixture(cs, *, execucao_id="execucao-simulada"):
    documento = {"execucao_id": execucao_id, "ambiente_id": "ambiente-simulado",
                 "api_url": "http://teste", "usuarios": {u: c.usuario_id for u, c in cs.items()},
                 "configuracao_efetiva": {"agente_real": True, "provedor": "ollama", "modelo": "simulado",
                                         "backend_id": "backend-simulado", "backend_historico_id": "backend-simulado",
                                         "commit_api": "commit-simulado"}, "eventos": {}}
    for uid, c in cs.items():
        evento = Evento(f"{uid}/s1/preflight", uid, 1, "preflight")
        documento["eventos"][evento.id] = evidencia_fixture(documento, evento, {
            "alvos_ativos": 0, "alvos_substituidos": 0, "alvos_no_historico": 0})
    return documento


def evidencia_fixture(documento, evento, observacao):
    from datetime import datetime, timezone
    return {"execucao_id": documento["execucao_id"], "ambiente_id": documento["ambiente_id"],
            "usuario_id": evento.usuario_id, "usuario_api_id": documento["usuarios"][evento.usuario_id],
            "sessao": evento.sessao, "evento_id": evento.id, "tipo": evento.tipo, "chaves": list(evento.chaves),
            "aprovado": True, "responsavel": "fixture-simulada", "referencia": "teste-sem-aprovacao-real",
            "origem": "cliente-falso", "coletado_em": datetime.now(timezone.utc).isoformat(),
            "observacao": observacao}


def test_plano_preserva_fonte_quatro_usuarios_20_sessoes_21_perguntas(dados):
    antes = copy.deepcopy(dados)
    eventos = integrado.planejar(dados)
    assert len({e.id for e in eventos}) == len(eventos)
    assert sum(e.tipo == "iniciar_sessao" for e in eventos) == 20
    assert sum(e.tipo == "pergunta" for e in eventos) == 21
    assert sum(e.tipo == "fato" for e in eventos) == 31
    assert sum(e.tipo == "esquecer_chaves" for e in eventos) == 1
    assert sum(e.tipo == "apagar_usuario" for e in eventos) == 1
    assert [e.usuario_id for e in eventos if e.tipo == "iniciar_sessao"] == ["u01", "u02", "u03", "u04"] * 5
    for usuario in dados["usuarios"]:
        uid = usuario["usuario_id"]
        assert [e.texto for e in eventos if e.usuario_id == uid and e.tipo == "fato"] == [
            f["texto"] for s in usuario["sessoes"] for f in s.get("fatos", [])]
        assert [e.texto for e in eventos if e.usuario_id == uid and e.tipo == "pergunta"] == [
            q["pergunta"] for q in usuario["perguntas"]]
    assert dados == antes


def test_execucao_integral_simulada_incremental_continuidade_e_metricas(dados, tmp_path):
    log = tmp_path / "execucao.jsonl"

    def conferir_incremento(evento):
        linhas = ler_log(log)
        assert linhas[-1]["tipo"] == "tentativa"
        assert linhas[-1]["evento"]["id"] == evento.id
        if evento.tipo == "pergunta":
            assert any(l["tipo"] == "resultado" for l in linhas)

    ts = clientes(observar=conferir_incremento)
    antes = copy.deepcopy(dados)
    r = integrado.executar(dados, ts, log, provedor="ollama", modelo="simulado")
    assert dados == antes
    assert r["simulado"] is True
    assert r["falhas"] == 0
    assert len(r["sessoes"]) == 40
    assert sum(s["perguntas"] == 0 for s in r["sessoes"]) == 12
    for cenario, t in ts.items():
        sessoes = [s for s in r["sessoes"] if s["cenario"] == cenario]
        assert len(sessoes) == 20
        assert sum(s["perguntas"] for s in sessoes) == 21
        assert t.fechar_chamadas == 1
        for s in sessoes:
            tok = s["tokens"]
            assert tok["sessao"]["tokens_total"] == tok["ingestao"]["tokens_total"] + tok["perguntas"]["tokens_total"]
            if s["perguntas"] == 0:
                assert tok["perguntas"]["tokens_total"] == 0
        for medida in r["metricas_resposta"][cenario].values():
            assert medida["taxa_pct"] is None
            assert medida["aplicabilidade_desconhecida"] == 21
    assert ts["historico_completo"].maior_historico["u01"] == 15
    assert ts["memoria_automatica"].maior_historico["u01"] < 10
    assert "cidade" in ts["memoria_automatica"].memorias["u01"]
    assert "carro" not in ts["memoria_automatica"].memorias["u02"]
    assert set(ts["memoria_automatica"].memorias["u04"]) == {"cidade"}
    assert all(m["pares_medidos"] == 20 for etapa in r["comparacoes_tokens"].values() for m in etapa.values())
    registros = ler_log(log)
    assert registros[0]["tipo"] == "inicio"
    assert registros[0]["commit"]
    assert registros[-1]["tipo"] == "fim"
    assert any(l.get("checkpoint") == "verificado_simulado" for l in registros)
    assert not any(l.get("checkpoint") == "verificado" for l in registros)
    assert all(r["julgamento"]["revisao_necessaria"] for r in r["resultados"] if r["evento"]["tipo"] == "pergunta")


def test_falha_preserva_parcelas_e_nao_repete_operacao(dados, tmp_path):
    ts = clientes(falhar="u01/s1/fato2")
    r = integrado.executar(dados, ts, tmp_path / "parcial.jsonl")
    for s in r["sessoes"]:
        if s["usuario_id"] == "u01" and s["sessao"] == 1:
            tok = s["tokens"]["sessao"]
            assert s["estado"] == "incompleta"
            assert tok["tokens_total"] is None
            assert tok["tokens_total_observados"] == 24
            assert tok["chamadas_previstas"] == 3
            assert tok["chamadas_observadas"] == 2
            assert tok["chamadas_modelo"] is None
    assert all(not q["trajetoria_integra"] for q in r["resultados"]
               if q["evento"]["usuario_id"] == "u01" and q["evento"]["tipo"] == "pergunta")


def test_interrupcao_fecha_clientes_e_mantem_jsonl_parcial(dados, tmp_path):
    ts = clientes(interromper="u01/s1/fato2")
    saida = tmp_path / "interrompido.jsonl"
    with pytest.raises(KeyboardInterrupt):
        integrado.executar(dados, ts, saida)
    log = ler_log(saida)
    assert log[-1]["tipo"] == "interrupcao"
    assert any(l["tipo"] == "resultado" for l in log)
    assert not any(l["tipo"] == "fim" for l in log)
    assert all(t.fechar_chamadas == 1 for t in ts.values())


def test_nao_sobrescreve_e_validacao_nao_executa_transporte(dados, tmp_path):
    saida = tmp_path / "existente.jsonl"
    saida.write_text("original", encoding="utf-8")
    ts = clientes()
    with pytest.raises(FileExistsError):
        integrado.executar(dados, ts, saida)
    assert saida.read_text(encoding="utf-8") == "original"
    assert all(not t.eventos for t in ts.values())
    invalido = copy.deepcopy(dados)
    invalido["usuarios"][0]["sessoes"].pop()
    with pytest.raises(ValueError, match="sessões"):
        integrado.executar(invalido, ts, tmp_path / "nao_criado.jsonl")
    assert not (tmp_path / "nao_criado.jsonl").exists()


def test_checkpoints_nao_confundem_busca_vazia_com_exclusao_ou_sessao_com_reinicio():
    persistencia = Evento("p", "u", 1, "checkpoint_persistencia")
    exclusao = Evento("e", "u", 1, "checkpoint_exclusao")
    for evento in (persistencia, exclusao):
        assert integrado.classificar_checkpoint(evento, {"estado_regras": {}}, cenario="memoria_automatica", simulado=False) == "nao_verificado"
    assert integrado.classificar_checkpoint(persistencia, {
        "reinicio_confirmado": True, "estado_antes": {}, "estado_depois": {},
    }, cenario="memoria_automatica", simulado=False) == "nao_verificado"
    assert integrado.classificar_checkpoint(exclusao, {
        "alvos_ativos": 0, "alvos_substituidos": 1, "alvos_no_historico": 0,
        "nao_alvos_preservados": True,
    }, cenario="memoria_automatica", simulado=False) == "nao_verificado"


def test_http_recusa_contrato_ausente_antes_da_primeira_requisicao(dados, tmp_path):
    pedidos = Mock(side_effect=AssertionError("HTTP não deveria ser chamado"))
    executor = Mock(side_effect=AssertionError("LLM real proibida"))
    with httpx.Client(base_url="http://teste", transport=httpx.MockTransport(pedidos)) as cliente:
        credenciais = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
        ts = {"memoria_automatica": TransporteHTTP(cliente, credenciais),
              "historico_completo": TransporteHistorico(executor=executor)}
        with pytest.raises(ValueError, match="esquecer_chaves exige"):
            integrado.executar(dados, ts, tmp_path / "nao_criado.jsonl")
    pedidos.assert_not_called()
    executor.assert_not_called()
    assert not (tmp_path / "nao_criado.jsonl").exists()


def test_http_usa_textos_literais_token_por_usuario_e_endpoints_existentes(dados, tmp_path):
    eventos = integrado.planejar(dados)
    pedidos = []

    def responder(request):
        pedidos.append(request)
        if request.url.path == "/provedores":
            return httpx.Response(200, json=[{"provedor": "ollama", "modelo": "simulado", "configurado": True}])
        if request.url.path.endswith("/sessoes"):
            return httpx.Response(204)
        if request.url.path == "/conversas":
            return httpx.Response(200, json={"resposta": "simulado", "tokens_entrada": 5, "tokens_saida": 1})
        return httpx.Response(200, json={})

    with httpx.Client(base_url="http://teste", transport=httpx.MockTransport(responder)) as cliente:
        cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-" + u["usuario_id"]) for u in dados["usuarios"]}
        evidencia = tmp_path / "evidencias.json"
        evidencia.write_text(json.dumps(documento_fixture(cs)), encoding="utf-8")
        t = TransporteHTTP(cliente, cs, contratos=contrato_fixture(eventos),
                           verificar_checkpoint=VerificadorEvidencias(evidencia))
        t.validar(eventos)
        t.verificar_inicio(eventos, execucao_id="execucao-simulada", provedor="ollama", modelo="simulado")
        selecionados = [next(e for e in eventos if e.usuario_id == "u01" and e.tipo == tipo)
                        for tipo in ("iniciar_sessao", "fato", "pergunta", "checkpoint_persistencia")]
        selecionados += [next(e for e in eventos if e.tipo == "apagar_usuario")]
        for evento in selecionados:
            t.executar(evento, provedor="ollama", modelo="simulado")
        conversas = [r for r in pedidos if r.url.path == "/conversas"]
        assert [json.loads(r.content)["mensagem"] for r in conversas] == [e.texto for e in selecionados if e.tipo in {"fato", "pergunta"}]
        assert all(set(json.loads(r.content)) == {"usuario_id", "mensagem", "provedor", "modelo"} for r in conversas)
        for r in pedidos:
            if r.url.path == "/provedores":
                continue
            uid = json.loads(r.content)["usuario_id"] if r.url.path == "/conversas" else r.url.path.split("/")[2]
            assert r.headers["Authorization"] == "Bearer token-" + uid.removeprefix("p6_")
        assert any(r.method == "DELETE" and r.url.path == "/usuarios/p6_u04/memorias" for r in pedidos)
        assert all(not r.url.path.endswith("/memorias") or r.method == "DELETE" for r in pedidos)
    assert "token-u01" not in repr(cs["u01"])


def test_historico_reutiliza_p1_p2_sem_repetir_prefixos_e_segmenta_apagamento(dados):
    eventos = integrado.planejar(dados)
    lotes = []

    def executar(caso, provedor, modelo, *, timeout):
        lotes.append(list(caso["mensagens"]))
        assert provedor == "ollama" and modelo == "simulado" and timeout == 42
        return [{"resposta": "simulado", "tokens_entrada": 5, "tokens_saida": 1,
                 "latencia_ms": 1} for _ in caso["mensagens"]]

    t = TransporteHistorico(contratos=contrato_fixture(eventos), timeout=42, executor=executar)
    t.validar(eventos)
    for e in eventos:
        resposta = t.executar(e, provedor="ollama", modelo="simulado")
        if e.tipo in integrado.MODELO_EVENTOS:
            assert resposta["memorias_usadas"] == []
            assert resposta["origem"] == "lote_spawn"
    assert len(lotes) == 5  # quatro usuários; u04 tem novo episódio após apagar tudo
    mensagens_u01 = [e.texto for e in eventos if e.usuario_id == "u01" and e.tipo in {"fato", "pergunta"}]
    assert lotes[0] == mensagens_u01
    assert len(lotes[0]) == 15
    assert not any("Porto Alegre" in m or "Florianópolis" in m for m in lotes[-1])
    assert sum(len(lote) for lote in lotes) == 53
    t.fechar()
    assert not t._resultados


def test_historico_nao_reexecuta_lote_com_falha(dados):
    eventos = integrado.planejar(dados)
    executor = Mock(side_effect=TimeoutError("simulado"))
    t = TransporteHistorico(contratos=contrato_fixture(eventos), executor=executor)
    t.validar(eventos)
    fatos = [e for e in eventos if e.usuario_id == "u01" and e.tipo == "fato"][:2]
    for e in fatos:
        with pytest.raises(RuntimeError, match="desconhecido"):
            t.executar(e, provedor="ollama", modelo="simulado")
    assert executor.call_count == 1


def test_anotacoes_invalidas_nao_criam_saida_nem_iniciam_clientes(dados, tmp_path):
    ts = clientes()
    with pytest.raises(ValueError):
        integrado.executar(dados, ts, tmp_path / "nao_criado.jsonl", anotacoes={"inexistente": {}})
    assert not (tmp_path / "nao_criado.jsonl").exists()
    assert all(not t.eventos for t in ts.values())


def test_cli_sem_executar_so_valida_plano(monkeypatch, capsys):
    monkeypatch.setattr(integrado.sys, "argv", ["avaliar_sessoes_integradas"])
    assert integrado.main() == 0
    resumo = json.loads(capsys.readouterr().out)
    assert resumo["sessoes"] == 20 and resumo["perguntas"] == 21
    assert resumo["acoes_que_exigem_contrato"] == ["u02/s5/esquecer_chaves"]


@pytest.mark.parametrize("falhar", [None, "u01/s1/fato2"])
def test_anotacao_explicita_p4_nao_aprova_trajetoria_incompleta(dados, tmp_path, falhar):
    ts = clientes(falhar=falhar)
    qid = "u01/s2/pergunta1"
    for t in ts.values():
        original = t.executar

        def responder(e, *, provedor, modelo, original=original):
            r = original(e, provedor=provedor, modelo=modelo)
            if e.id == qid:
                r["resposta"] = "Osasco"  # resposta simulada, presente na fonte
            return r

        t.executar = responder
    anotacoes = {qid: {"categoria": "recuperacao", "esperado": "Osasco",
                      "avaliacao": {"tipo_resposta": "factual", "atributo": "cidade",
                                    "informacoes_proibidas": []}}}
    antes = copy.deepcopy(anotacoes)
    r = integrado.executar(dados, ts, tmp_path / "anotado.jsonl", anotacoes=anotacoes)
    for cenario in integrado.CENARIOS:
        medida = r["metricas_resposta"][cenario]["recuperacao_factual"]
        assert medida["tentativas_elegiveis"] == 1
        assert medida["numerador"] == (0 if falhar else 1)
        assert medida["denominador"] == (0 if falhar else 1)
        assert medida["taxa_pct"] == (None if falhar else 100.0)
    assert anotacoes == antes


def test_comparacao_descarta_duplicatas_e_zeros_sem_origem_verificavel():
    m = integrado.tokens_etapa([{"tokens_entrada": 10, "tokens_saida": 2}])
    sessoes = [{"usuario_id": "u01", "sessao": 1, "cenario": c,
                "tokens": {k: copy.deepcopy(m) for k in ("ingestao", "perguntas", "sessao")}}
               for c in integrado.CENARIOS]
    duplicados = integrado.comparar_sessoes([*sessoes, copy.deepcopy(sessoes[0])])
    assert duplicados["sessao"]["tokens_total"]["chaves_duplicadas_descartadas"] == 1
    assert duplicados["sessao"]["tokens_total"]["reducao_pct"] is None
    sessoes[0]["tokens"]["sessao"] = integrado.tokens_etapa([{"tokens_entrada": 0, "tokens_saida": 2}])
    incompletos = integrado.comparar_sessoes(sessoes)
    assert incompletos["sessao"]["tokens_total"]["reducao_pct"] is None
    assert incompletos["sessao"]["tokens_saida"]["pares_medidos"] == 1


def test_cli_execucao_http_recusa_contrato_ausente_sem_llm(dados, monkeypatch, tmp_path, capsys):
    credenciais = tmp_path / "credenciais.json"
    credenciais.write_text(json.dumps({u["usuario_id"]: {
        "usuario_id": "p6_" + u["usuario_id"], "token": "token-falso",
    } for u in dados["usuarios"]}), encoding="utf-8")
    saida = tmp_path / "nao_criado.jsonl"
    requisicoes = Mock(side_effect=AssertionError("HTTP proibido"))
    cliente = httpx.Client(base_url="http://teste", transport=httpx.MockTransport(requisicoes))
    executor = Mock(side_effect=AssertionError("LLM real proibida"))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: cliente)
    historico = TransporteHistorico
    monkeypatch.setattr(integrado, "TransporteHistorico", lambda **kwargs: historico(**kwargs, executor=executor))
    monkeypatch.setattr(integrado.sys, "argv", ["avaliar_sessoes_integradas", "--executar",
                        "--credenciais", str(credenciais), "--saida", str(saida)])
    with pytest.raises(SystemExit) as erro:
        integrado.main()
    assert erro.value.code == 2
    assert "esquecer_chaves exige" in capsys.readouterr().err
    requisicoes.assert_not_called()
    executor.assert_not_called()
    assert not saida.exists()


def test_falha_fechamento_e_preservada_no_relatorio(dados, tmp_path):
    ts = clientes()
    ts["memoria_automatica"].fechar = Mock(side_effect=OSError("simulado"))
    log = tmp_path / "fechamento.jsonl"
    r = integrado.executar(dados, ts, log)
    assert r["estado_orquestracao"] == "incompleta"
    assert r["falhas_fechamento"] == [{"cenario": "memoria_automatica", "tipo": "OSError"}]
    assert ler_log(log)[-2]["tipo"] == "falhas_fechamento"


def test_clientes_compartilhados_nao_podem_misturar_cenarios(dados, tmp_path):
    t = ClienteFalso("memoria_automatica")
    with pytest.raises(ValueError, match="independentes"):
        integrado.executar(dados, {c: t for c in integrado.CENARIOS}, tmp_path / "nao_criado.jsonl")
    assert not t.eventos


@pytest.mark.parametrize("bloqueio", ["401", "403", "500", "estado", "sem_evidencia", "inativos", "historico", "sem_aprovacao"])
def test_barreira_global_bloqueia_ambos_cenarios_sem_gerar_respostas(dados, tmp_path, bloqueio):
    eventos = integrado.planejar(dados)
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "segredo-" + u["usuario_id"])
          for u in dados["usuarios"]}
    documento = documento_fixture(cs)
    if bloqueio in {"inativos", "historico"}:
        campo = "alvos_substituidos" if bloqueio == "inativos" else "alvos_no_historico"
        documento["eventos"]["u04/s1/preflight"]["observacao"][campo] = 1
    if bloqueio == "sem_aprovacao":
        documento["eventos"]["u04/s1/preflight"]["aprovado"] = False
    caminho = tmp_path / "evidencia.json"
    caminho.write_text(json.dumps(documento), encoding="utf-8")
    pedidos = []

    def responder(request):
        pedidos.append(request)
        assert request.method == "GET"  # proíbe fatos, perguntas, exclusão e resets
        if "p6_u04" in request.url.path:
            if bloqueio.isdigit():
                return httpx.Response(int(bloqueio), json={})
            if bloqueio == "estado":
                return httpx.Response(200, json={"cidade": "estado-incompativel-simulado"})
        return httpx.Response(200, json={})

    cliente = httpx.Client(base_url="http://teste", transport=httpx.MockTransport(responder))
    automatico = TransporteHTTP(cliente, cs, contratos=contrato_fixture(eventos),
                               verificar_checkpoint=VerificadorEvidencias(None if bloqueio == "sem_evidencia" else caminho))
    executor = Mock(side_effect=AssertionError("Nenhum modelo pode iniciar antes da barreira global"))
    historico = TransporteHistorico(contratos=contrato_fixture(eventos), executor=executor)
    log = tmp_path / "bloqueio.jsonl"
    r = integrado.executar(dados, {"memoria_automatica": automatico, "historico_completo": historico},
                          log, modelo="simulado", execucao_id="execucao-simulada")
    assert r["estado_orquestracao"] == "incompleta"
    assert len(pedidos) == 4
    executor.assert_not_called()
    assert not r["resultados"] and not r["sessoes"]
    assert cliente.is_closed
    assert ler_log(log)[-1]["tipo"] == "fim"
    assert "segredo-" not in log.read_text(encoding="utf-8")
    assert not any(l["tipo"] == "tentativa" for l in ler_log(log))
    assert r["perguntas_observadas"] == dict.fromkeys(integrado.CENARIOS, 0)
    assert r["metricas_recuperacao_lexical"]["memoria_automatica"]["esperado_presente"]["nao_verificados"] == 17
    assert r["metricas_checkpoints"]["memoria_automatica"]["checkpoint_persistencia"]["nao_verificados"] == 20


def test_transporte_http_nao_admite_uso_direto_sem_barreira(dados):
    pedido = Mock(side_effect=AssertionError("HTTP proibido"))
    with httpx.Client(base_url="http://teste", transport=httpx.MockTransport(pedido)) as cliente:
        cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
        t = TransporteHTTP(cliente, cs)
        with pytest.raises(ValueError, match="operacional inicial"):
            t.executar(next(e for e in integrado.planejar(dados) if e.tipo == "fato"),
                       provedor="ollama", modelo="simulado")
    pedido.assert_not_called()


@pytest.mark.parametrize("campo,valor", [
    ("execucao_id", "outra"), ("ambiente_id", "outro"), ("usuario_id", "u02"),
    ("usuario_api_id", "p6_outro"), ("sessao", 2), ("sessao", True),
    ("evento_id", "outro"), ("tipo", "checkpoint_exclusao"), ("chaves", ["outro"]),
    ("aprovado", False), ("responsavel", ""), ("referencia", ""), ("origem", ""),
    ("coletado_em", "2000-01-01T00:00:00+00:00"), ("coletado_em", "2999-01-01T00:00:00+00:00"),
    ("coletado_em", "2000-01-01T00:00:00"),
])
def test_verificador_recusa_evidencia_incompativel(dados, tmp_path, campo, valor):
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    caminho = tmp_path / "evidencia.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    v = VerificadorEvidencias(caminho)
    v.preparar(execucao_id="execucao-simulada", api_url="http://teste", usuarios=doc["usuarios"],
               provedor="ollama", modelo="simulado")
    e = Evento("u01/s1/checkpoint_persistencia", "u01", 1, "checkpoint_persistencia")
    doc["eventos"][e.id] = evidencia_fixture(doc, e, {
        "reinicio_confirmado": True, "estado_antes": {"a": "b"}, "estado_depois": {"a": "b"}})
    doc["eventos"][e.id][campo] = valor
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError):
        v(e)


@pytest.mark.parametrize("alteracao", ["ambiente", "api", "usuarios", "configuracao", "json"])
def test_verificador_recusa_mudanca_do_documento_durante_execucao(dados, tmp_path, alteracao):
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    caminho = tmp_path / "evidencia.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    v = VerificadorEvidencias(caminho)
    v.preparar(execucao_id="execucao-simulada", api_url="http://teste", usuarios=doc["usuarios"],
               provedor="ollama", modelo="simulado")
    if alteracao == "ambiente":
        doc["ambiente_id"] = "outro"
    elif alteracao == "api":
        doc["api_url"] = "http://outra"
    elif alteracao == "usuarios":
        doc["usuarios"]["u01"] = "p6_outro"
    elif alteracao == "configuracao":
        doc["configuracao_efetiva"]["modelo"] = "outro"
    caminho.write_text("{" if alteracao == "json" else json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError):
        v(Evento("u01/s1/checkpoint_persistencia", "u01", 1, "checkpoint_persistencia"))


def test_evidencia_ausente_nao_verifica_e_exclusao_exige_alvos_anteriores(dados, tmp_path):
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    caminho = tmp_path / "evidencia.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    v = VerificadorEvidencias(caminho)
    v.preparar(execucao_id="execucao-simulada", api_url="http://teste", usuarios=doc["usuarios"],
               provedor="ollama", modelo="simulado")
    e = Evento("u04/s4/checkpoint_exclusao", "u04", 4, "checkpoint_exclusao")
    assert v(e) == {"evidencia_status": "ausente"}
    observacao = {"alvos_ativos": 0, "alvos_substituidos": 0,
                  "alvos_no_historico": 0, "nao_alvos_preservados": True}
    doc["eventos"][e.id] = evidencia_fixture(doc, e, observacao)
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="antes da ação"):
        v(e)
    observacao["alvos_antes"] = 3
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    resultado = v(e)
    assert integrado.classificar_checkpoint(e, resultado, cenario="memoria_automatica", simulado=False) == "verificado"
    assert len(resultado["evidencia"]["documento_sha256"]) == 64
    resultado["alvos_substituidos"] = 1
    assert integrado.classificar_checkpoint(e, resultado, cenario="memoria_automatica", simulado=False) == "reprovado"
    resultado.pop("alvos_substituidos")
    assert integrado.classificar_checkpoint(e, resultado, cenario="memoria_automatica", simulado=False) == "nao_verificado"


def test_anotacoes_parciais_incompativeis_nao_inventam_politicas(dados, tmp_path):
    anotacoes = {
        "u01/s2/pergunta1": {"categoria": "recuperacao", "esperado": "Osasco",
                              "avaliacao": {"tipo_resposta": "factual", "atributo": "cidade", "informacoes_proibidas": []}},
        "u03/s2/pergunta1": {"categoria": "recuperacao", "esperado": "Luna",
                              "avaliacao": {"tipo_resposta": "factual", "atributo": "animais", "informacoes_proibidas": []}},
    }
    antes = copy.deepcopy(anotacoes)
    r = integrado.executar(dados, clientes(), tmp_path / "parcial.jsonl", anotacoes=anotacoes)
    cobertura = r["cobertura_anotacoes"]
    assert (cobertura["compativeis"], cobertura["incompativeis"], cobertura["ausentes"]) == (1, 1, 19)
    assert cobertura["denominador"] == 21 and cobertura["numerador"] == 1
    assert cobertura["cobertura_pct"] == 4.76
    assert r["avaliacao_respostas_completa"] is False
    invalidas = [q for q in r["resultados"] if q["evento"]["id"] == "u03/s2/pergunta1"]
    assert all(q["anotacao_estado"] == "incompativel" and q["julgamento"]["acerto_factual"]["status"] == "nao_verificado"
               for q in invalidas)
    assert anotacoes == antes
    auto = r["metricas_recuperacao_lexical"]["memoria_automatica"]
    assert auto["esperado_presente"]["denominador"] == 17
    assert auto["esperado_presente"]["numerador"] == 0
    assert auto["contexto_vazio_sem_esperado"]["numerador"] == 4
    assert all(m["nao_aplicaveis"] == 21 for m in r["metricas_recuperacao_lexical"]["historico_completo"].values())


def test_anotacoes_oficiais_p6_tem_cobertura_estrutural_completa(dados):
    from eval.julgamento_respostas import julgar_resposta

    caminho = RAIZ / "eval/memoria/anotacoes_p6.json"
    bytes_antes = caminho.read_bytes()
    anotacoes = json.loads(bytes_antes)
    eventos = integrado.planejar(dados)
    validas, cobertura = integrado.cobertura_anotacoes(eventos, anotacoes)
    assert len(validas) == 21
    assert (cobertura["compativeis"], cobertura["incompativeis"], cobertura["ausentes"]) == (21, 0, 0)
    assert cobertura["cobertura_pct"] == 100
    assert set(validas) == {e.id for e in eventos if e.tipo == "pergunta"}
    # Julga respostas de referência, não respostas observadas de um chatbot real.
    for qid, caso in validas.items():
        resposta = caso["esperado"] if caso["avaliacao"]["tipo_resposta"] == "factual" else "DESCONHECIDO"
        assert julgar_resposta(resposta, caso)["protocolo_ok"] is True, qid
    assert caminho.read_bytes() == bytes_antes


def test_gatos_preserva_gabaritos_distintos_aguardando_revisao_semantica(dados):
    anotacoes = json.loads((RAIZ / "eval/memoria/anotacoes_p6.json").read_text(encoding="utf-8"))
    usuario = next(u for u in dados["usuarios"] if u["usuario_id"] == "u03")
    pergunta = usuario["perguntas"][2]
    assert pergunta["pergunta"] == "Quantos gatos eu tenho?"
    assert pergunta["esperado"] == ["Luna", "Simba"]  # alvos de recuperação
    anotacao = anotacoes["u03/s4/pergunta3"]
    assert anotacao["avaliacao"]["atributo"] == "quantidade_pets"
    assert anotacao["esperado"] == "dois"  # gabarito de resposta proposto por Vinicius
    assert anotacao["avaliacao"]["aliases_aceitos"] == ["2"]
    # Compatibilidade estrutural não certifica a revisão humana dessa interpretação.


@pytest.mark.parametrize("estado,codigo", [("concluida", 0), ("incompleta", 1)])
def test_cli_retorna_estado_orquestracao_preservando_jsonl(dados, monkeypatch, tmp_path, estado, codigo):
    cs = tmp_path / "credenciais.json"
    cs.write_text(json.dumps({u["usuario_id"]: {"usuario_id": "p6_" + u["usuario_id"], "token": "token-falso"}
                              for u in dados["usuarios"]}), encoding="utf-8")
    saida = tmp_path / "execucao.jsonl"
    ts = clientes(falhar="u01/s1/fato2" if estado == "incompleta" else None)
    monkeypatch.setattr(integrado, "TransporteHTTP", lambda *a, **kw: ts["memoria_automatica"])
    monkeypatch.setattr(integrado, "TransporteHistorico", lambda **kw: ts["historico_completo"])
    cliente = httpx.Client(base_url="http://teste", transport=httpx.MockTransport(Mock(side_effect=AssertionError("HTTP proibido"))))
    monkeypatch.setattr(httpx, "Client", lambda **kw: cliente)
    monkeypatch.setattr(integrado.sys, "argv", ["p6", "--executar", "--saida", str(saida), "--credenciais", str(cs)])
    assert integrado.main() == codigo
    assert ler_log(saida)[-1]["estado_orquestracao"] == estado
    assert cliente.is_closed


def test_recuperacao_ausente_ou_trajetoria_incompleta_nao_vira_sucesso():
    referencia = {"esperado": ["Santos"], "proibido": ["Osasco"]}
    for valores, integra in ((None, True), ([], False), (["Santos"], False)):
        r = {"cenario": "memoria_automatica", "estado": "concluido", "trajetoria_integra": integra,
             "resultado": {"memorias_usadas": valores}}
        assert integrado.avaliar_recuperacao(r, referencia)["esperado_presente"] is None
    r = {"cenario": "memoria_automatica", "estado": "concluido", "trajetoria_integra": True,
         "resultado": {"memorias_usadas": ["Moro em Santos, antes em Osasco."]}}
    assert integrado.avaliar_recuperacao(r, referencia)["esperado_presente"] is True
    assert integrado.avaliar_recuperacao(r, referencia)["proibido_presente"] is True


@pytest.mark.parametrize("modelo_api", ["simulado", "incompativel"])
def test_http_integrado_simulado_preserva_proveniencia_tokens_e_checkpoints_ausentes(dados, tmp_path, modelo_api):
    eventos = integrado.planejar(dados)
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "segredo-nao-registrar") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    doc["configuracao_efetiva"]["token_privado"] = "segredo-nao-registrar"
    caminho = tmp_path / "evidencias.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    pedidos = []

    def responder(request):
        pedidos.append(request)
        if request.url.path == "/provedores":
            return httpx.Response(200, json=[{"provedor": "ollama", "modelo": "simulado", "configurado": True}])
        if request.url.path == "/conversas":
            return httpx.Response(200, json={"resposta": "resposta simulada", "memorias_usadas": [],
                                           "provedor": "ollama", "modelo": modelo_api,
                                           "tokens_entrada": 5, "tokens_saida": 1, "latencia_ms": 2})
        if request.url.path.endswith("/sessoes"):
            return httpx.Response(204)
        return httpx.Response(200, json={})

    def executar_lote(caso, provedor, modelo, **kwargs):
        return [{"resposta": "resposta simulada", "tokens_entrada": 5, "tokens_saida": 1, "latencia_ms": 1}
                for _ in caso["mensagens"]]

    cliente = httpx.Client(base_url="http://teste", transport=httpx.MockTransport(responder))
    ts = {"memoria_automatica": TransporteHTTP(cliente, cs, contratos=contrato_fixture(eventos),
                                              verificar_checkpoint=VerificadorEvidencias(caminho)),
          "historico_completo": TransporteHistorico(contratos=contrato_fixture(eventos), executor=executar_lote)}
    for t in ts.values():
        t.simulado = True
    log = tmp_path / "http-simulado.jsonl"
    r = integrado.executar(dados, ts, log, modelo="simulado", execucao_id="execucao-simulada")
    assert r["estado_orquestracao"] == ("concluida" if modelo_api == "simulado" else "incompleta")
    assert r["avaliacao_respostas_completa"] is False
    assert all(p.method == "GET" for p in pedidos[:4])
    assert {p.url.path for p in pedidos[:4]} == {f"/usuarios/p6_{u}/estado-regras" for u in cs}
    assert sum(p.url.path == "/conversas" for p in pedidos) == 53
    assert len(r["sessoes"]) == 40
    assert r["proveniencia"]["memoria_automatica"]["usuarios"] == doc["usuarios"]
    assert r["proveniencia"]["memoria_automatica"]["ambiente_id"] == doc["ambiente_id"]
    assert all(q["resultado"]["configuracao_compativel"] is (modelo_api == "simulado") for q in r["resultados"]
               if q["cenario"] == "memoria_automatica" and q["evento"]["tipo"] == "pergunta")
    for s in r["sessoes"]:
        assert s["tokens"]["sessao"]["cobertura"]["entrada"]["cobertura_pct"] == 100.0
        assert s["tokens"]["sessao"]["tokens_total"] > 0
    assert r["comparacoes_tokens"]["sessao"]["tokens_total"]["pares_medidos"] == (20 if modelo_api == "simulado" else 0)
    for medida in r["metricas_checkpoints"]["memoria_automatica"].values():
        assert medida["numerador"] == medida["denominador"] == 0
        assert medida["cobertura_pct"] == 0.0
        assert medida["taxa_pct"] is None
    conteudo = log.read_text(encoding="utf-8")
    assert "segredo-nao-registrar" not in conteudo
    assert ler_log(log)[0]["identificacao_transportes"]["memoria_automatica"]["usuarios"] == doc["usuarios"]


@pytest.mark.parametrize("campo,valor", [("agente_real", False), ("modelo", "outro"),
                                        ("provedor", "outro"), ("backend_historico_id", "outro"),
                                        ("backend_id", ""), ("commit_api", "")])
def test_configuracao_externa_incompativel_bloqueia_preparacao(dados, tmp_path, campo, valor):
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    doc["configuracao_efetiva"][campo] = valor
    caminho = tmp_path / "evidencias.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="Configuração efetiva"):
        VerificadorEvidencias(caminho).preparar(execucao_id="execucao-simulada", api_url="http://teste",
                                              usuarios=doc["usuarios"], provedor="ollama", modelo="simulado")


def test_cli_preflight_http_recusado_retorna_um_e_mantem_jsonl(dados, monkeypatch, tmp_path):
    cs = tmp_path / "credenciais.json"
    cs.write_text(json.dumps({u["usuario_id"]: {"usuario_id": "p6_" + u["usuario_id"], "token": "token-falso"}
                              for u in dados["usuarios"]}), encoding="utf-8")
    contratos = tmp_path / "contratos.json"
    contratos.write_text(json.dumps(contrato_fixture(integrado.planejar(dados))), encoding="utf-8")
    chamadas = []

    def rejeitar(r):
        chamadas.append(r)
        assert r.method == "GET"
        return httpx.Response(401, json={})

    cliente = httpx.Client(base_url="http://teste", transport=httpx.MockTransport(rejeitar))
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: cliente)
    historico = TransporteHistorico
    executor = Mock(side_effect=AssertionError("LLM proibida"))
    monkeypatch.setattr(integrado, "TransporteHistorico", lambda **kw: historico(**kw, executor=executor))
    saida = tmp_path / "recusado.jsonl"
    monkeypatch.setattr(integrado.sys, "argv", ["p6", "--executar", "--credenciais", str(cs),
                                              "--contratos-acoes", str(contratos), "--saida", str(saida)])
    assert integrado.main() == 1
    assert len(chamadas) == 4
    executor.assert_not_called()
    assert ler_log(saida)[-1]["estado_orquestracao"] == "incompleta"


def test_checkpoint_persistencia_compativel_e_rejeicao_de_snapshot_antigo(dados, tmp_path):
    from datetime import datetime, timedelta, timezone
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    caminho = tmp_path / "evidencias.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    v = VerificadorEvidencias(caminho)
    v.preparar(execucao_id="execucao-simulada", api_url="http://teste", usuarios=doc["usuarios"],
               provedor="ollama", modelo="simulado")
    e = Evento("u01/s2/checkpoint_persistencia", "u01", 2, "checkpoint_persistencia")
    v.marcar_acao(Evento("u01/s2/pergunta1", "u01", 2, "pergunta"))
    doc["eventos"][e.id] = evidencia_fixture(doc, e, {
        "reinicio_confirmado": True, "estado_antes": {"a": "b"}, "estado_depois": {"a": "b"}})
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    r = v(e)
    assert integrado.classificar_checkpoint(e, r, cenario="memoria_automatica", simulado=False) == "verificado"
    doc["eventos"][e.id]["coletado_em"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="data da evidência"):
        v(e)


@pytest.mark.parametrize("catalogo", [None, {}, [], [
    {"provedor": "ollama", "modelo": "simulado", "configurado": False}], [
    {"provedor": "ollama", "modelo": "outro", "configurado": True}]])
def test_catalogo_incompativel_impede_liberacao_do_transporte(dados, tmp_path, catalogo):
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
    caminho = tmp_path / "evidencias.json"
    caminho.write_text(json.dumps(documento_fixture(cs)), encoding="utf-8")
    pedidos = []

    def responder(request):
        pedidos.append(request)
        assert request.method == "GET"
        return httpx.Response(200, json=catalogo if request.url.path == "/provedores" else {})

    with httpx.Client(base_url="http://teste", transport=httpx.MockTransport(responder)) as cliente:
        t = TransporteHTTP(cliente, cs, verificar_checkpoint=VerificadorEvidencias(caminho))
        with pytest.raises(ValueError, match="não permitido ou não configurado"):
            t.verificar_inicio(integrado.planejar(dados), execucao_id="execucao-simulada",
                               provedor="ollama", modelo="simulado")
        assert len(pedidos) == 5
        with pytest.raises(ValueError, match="operacional inicial"):
            t.executar(next(e for e in integrado.planejar(dados) if e.tipo == "fato"),
                       provedor="ollama", modelo="simulado")


# P6 Etapa 3: relógio e transportes inteiramente simulados, sem rede/modelo real.
@pytest.fixture
def relogio_evidencia(monkeypatch):
    from eval import sessoes_evidencias as evidencias

    class Relogio:
        agora = 0.0

        def __init__(self):
            self.pausas = []
            self.publicar = lambda: None

        def dormir(self, segundos):
            self.pausas.append(segundos)
            self.agora += segundos
            self.publicar()

    relogio = Relogio()
    monkeypatch.setattr(evidencias.time, "monotonic", lambda: relogio.agora)
    monkeypatch.setattr(evidencias.time, "sleep", relogio.dormir)
    return relogio


@pytest.fixture
def evidencia_local(dados, tmp_path):
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "token-falso") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    caminho = tmp_path / "evidencias-espera.json"

    def salvar():
        caminho.write_text(json.dumps(doc), encoding="utf-8")

    salvar()
    v = VerificadorEvidencias(caminho)
    v.preparar(execucao_id="execucao-simulada", api_url="http://teste", usuarios=doc["usuarios"],
               provedor="ollama", modelo="simulado")
    return v, doc, salvar


def test_espera_documento_aparece_e_liga_proveniencia(evidencia_local, relogio_evidencia):
    import hashlib
    v, doc, salvar = evidencia_local
    e = Evento("u01/s1/checkpoint_persistencia", "u01", 1, "checkpoint_persistencia")

    def publicar():
        doc["eventos"][e.id] = evidencia_fixture(doc, e, {
            "reinicio_confirmado": True, "estado_antes": {"simulado": 1}, "estado_depois": {"simulado": 1}})
        salvar()

    # Mesmo o arquivo inteiro pode estar temporariamente ausente.
    v.caminho.unlink()
    relogio_evidencia.publicar = publicar
    r = v.aguardar(e, timeout=3, intervalo=1)
    assert relogio_evidencia.pausas == [1]
    assert r["evidencia"]["execucao_id"] == doc["execucao_id"]
    assert r["evidencia"]["documento_sha256"] == hashlib.sha256(v.caminho.read_bytes()).hexdigest()


@pytest.mark.parametrize("campo,valor", [
    ("execucao_id", "outra"), ("ambiente_id", "outro"), ("usuario_id", "u01"),
    ("usuario_api_id", "p6_outro"), ("sessao", 2), ("evento_id", "outro"),
    ("tipo", "checkpoint_persistencia"), ("chaves", []), ("aprovado", False),
    ("coletado_em", "2000-01-01T00:00:00+00:00"),
])
def test_espera_rejeita_incompativel_sem_nova_consulta(evidencia_local, relogio_evidencia, campo, valor):
    from eval.sessoes_evidencias import EvidenciaIncompativel
    v, doc, salvar = evidencia_local
    e = Evento("u02/s5/checkpoint_exclusao_chaves", "u02", 5, "checkpoint_exclusao", chaves=("carro",))
    doc["eventos"][e.id] = evidencia_fixture(doc, e, {
        "alvos_antes": 1, "alvos_ativos": 0, "alvos_substituidos": 0,
        "alvos_no_historico": 0, "nao_alvos_preservados": True})
    doc["eventos"][e.id][campo] = valor
    salvar()
    with pytest.raises(EvidenciaIncompativel):
        v.aguardar(e, timeout=3, intervalo=1)
    assert relogio_evidencia.pausas == []


@pytest.mark.parametrize("invalida", [None, [], "texto"])
def test_entrada_presente_invalida_nao_e_ausencia(evidencia_local, relogio_evidencia, invalida):
    from eval.sessoes_evidencias import EvidenciaIncompativel
    v, doc, salvar = evidencia_local
    e = Evento("u01/s1/checkpoint_persistencia", "u01", 1, "checkpoint_persistencia")
    doc["eventos"][e.id] = invalida
    salvar()
    with pytest.raises(EvidenciaIncompativel):
        v.aguardar(e, timeout=2, intervalo=1)
    assert not relogio_evidencia.pausas


@pytest.mark.parametrize("ram", [None, "ausente"])
def test_sqlite_limpo_com_ram_desconhecida_nao_aprova(evidencia_local, relogio_evidencia, ram):
    from eval.sessoes_evidencias import TimeoutEvidencia
    v, doc, salvar = evidencia_local
    e = Evento("u04/s4/checkpoint_exclusao", "u04", 4, "checkpoint_exclusao")
    observacao = {"alvos_antes": 2, "alvos_ativos": 0, "alvos_substituidos": 0,
                  "nao_alvos_preservados": True}
    if ram is None:
        observacao["alvos_no_historico"] = None
    doc["eventos"][e.id] = evidencia_fixture(doc, e, observacao)
    salvar()
    assert integrado.classificar_checkpoint(e, v(e), cenario="memoria_automatica", simulado=False) == "nao_verificado"
    with pytest.raises(TimeoutEvidencia):
        v.aguardar(e, timeout=2.5, intervalo=1)
    assert relogio_evidencia.pausas == [1, 1, .5]
    assert v(e).get("alvos_no_historico") is None


def test_medicao_contraditoria_libera_espera_e_reprova(evidencia_local, relogio_evidencia):
    v, doc, salvar = evidencia_local
    e = Evento("u04/s4/checkpoint_exclusao", "u04", 4, "checkpoint_exclusao")
    doc["eventos"][e.id] = evidencia_fixture(doc, e, {
        "alvos_antes": 2, "alvos_ativos": 0, "alvos_substituidos": 1,
        "alvos_no_historico": 0, "nao_alvos_preservados": False})
    salvar()
    r = v.aguardar(e, timeout=3, intervalo=1)
    assert integrado.classificar_checkpoint(e, r, cenario="memoria_automatica", simulado=False) == "reprovado"
    assert not relogio_evidencia.pausas


@pytest.mark.parametrize("valor", [-1, True, "0", 0.0])
def test_medicao_invalida_e_rejeitada(evidencia_local, relogio_evidencia, valor):
    from eval.sessoes_evidencias import EvidenciaIncompativel
    v, doc, salvar = evidencia_local
    e = Evento("u04/s4/checkpoint_exclusao", "u04", 4, "checkpoint_exclusao")
    doc["eventos"][e.id] = evidencia_fixture(doc, e, {
        "alvos_antes": 2, "alvos_ativos": 0, "alvos_substituidos": 0,
        "alvos_no_historico": valor, "nao_alvos_preservados": True})
    salvar()
    with pytest.raises(EvidenciaIncompativel):
        v.aguardar(e, timeout=3, intervalo=1)
    assert not relogio_evidencia.pausas


@pytest.mark.parametrize("campo", ["timeout", "intervalo"])
@pytest.mark.parametrize("valor", [0, -1, float("nan"), float("inf"), float("-inf"), True, "1"])
def test_prazos_positivos_finitos(evidencia_local, campo, valor):
    v, _, _ = evidencia_local
    prazos = {"timeout": 2, "intervalo": 1, campo: valor}
    with pytest.raises(ValueError, match="positivo e finito"):
        v.aguardar(Evento("p", "u01", 1, "checkpoint_persistencia"), **prazos)


def test_leitura_concluida_fora_do_prazo_nao_e_aceita(evidencia_local, relogio_evidencia, monkeypatch):
    from eval.sessoes_evidencias import TimeoutEvidencia
    v, doc, salvar = evidencia_local
    e = Evento("u01/s1/checkpoint_persistencia", "u01", 1, "checkpoint_persistencia")
    doc["eventos"][e.id] = evidencia_fixture(doc, e, {
        "reinicio_confirmado": True, "estado_antes": [1], "estado_depois": [1]})
    salvar()
    ler = v._ler

    def leitura_lenta():
        relogio_evidencia.agora += 3
        return ler()

    monkeypatch.setattr(v, "_ler", leitura_lenta)
    with pytest.raises(TimeoutEvidencia):
        v.aguardar(e, timeout=2, intervalo=1)


@pytest.mark.parametrize("modo", ["sucesso", "timeout", "incompativel"])
def test_espera_integrada_audita_para_e_nao_repete_efeitos(dados, tmp_path, relogio_evidencia, modo):
    eventos = integrado.planejar(dados)
    cs = {u["usuario_id"]: Credencial("p6_" + u["usuario_id"], "segredo-nao-registrar") for u in dados["usuarios"]}
    doc = documento_fixture(cs)
    caminho = tmp_path / "externo.json"
    caminho.write_text(json.dumps(doc), encoding="utf-8")
    log = tmp_path / "rodada.jsonl"
    pedidos = []

    def responder(r):
        pedidos.append((r.method, r.url.path, r.content))
        if r.url.path == "/provedores":
            return httpx.Response(200, json=[{"provedor": "ollama", "modelo": "simulado", "configurado": True}])
        if r.url.path.endswith("/sessoes"):
            return httpx.Response(204)
        if r.url.path == "/conversas":
            return httpx.Response(200, json={"resposta": "simulado", "provedor": "ollama", "modelo": "simulado",
                                           "tokens_entrada": 1, "tokens_saida": 1, "memorias_usadas": []})
        return httpx.Response(200, json={})

    cliente = httpx.Client(base_url="http://teste", transport=httpx.MockTransport(responder))
    v = VerificadorEvidencias(caminho)
    automatico = TransporteHTTP(cliente, cs, contratos=contrato_fixture(eventos), verificar_checkpoint=v)
    automatico.simulado = True
    historico = ClienteFalso("historico_completo")
    excluir = next(e for e in eventos if e.tipo == "checkpoint_exclusao")
    aguardar = v.aguardar
    consultas = []

    def esperar(e, **kwargs):
        antes = list(pedidos)

        def publicar():
            assert pedidos == antes  # nenhuma operação HTTP durante as consultas
            linhas = ler_log(log)
            assert linhas[-1]["tipo"] == "aguardando_evidencia"
            assert linhas[-1]["evento"]["id"] == e.id
            consultas.append(e.id)
            if modo == "timeout" and e.id == excluir.id:
                return
            obs = ({"alvos_antes": 2, "alvos_ativos": 0, "alvos_substituidos": 0,
                    "alvos_no_historico": 0, "nao_alvos_preservados": True}
                   if e.tipo == "checkpoint_exclusao" else
                   {"reinicio_confirmado": True, "estado_antes": ["simulado"], "estado_depois": ["simulado"]})
            doc["eventos"][e.id] = evidencia_fixture(doc, e, obs)
            if modo == "incompativel" and e.id == excluir.id:
                doc["eventos"][e.id]["ambiente_id"] = "outro"
            caminho.write_text(json.dumps(doc), encoding="utf-8")

        relogio_evidencia.publicar = publicar
        return aguardar(e, **kwargs)

    v.aguardar = esperar
    r = integrado.executar(dados, {"memoria_automatica": automatico, "historico_completo": historico},
                          log, modelo="simulado", execucao_id="execucao-simulada", aguardar_evidencias=True,
                          timeout_evidencia=2.5, intervalo_evidencia=1)
    linhas = ler_log(log)
    assert linhas[-1]["tipo"] == "fim"
    assert cliente.is_closed and historico.fechar_chamadas == 1
    assert "segredo-nao-registrar" not in log.read_text(encoding="utf-8")
    assert sum(m == "DELETE" for m, _, _ in pedidos) == 1
    assert len({e.id for e in historico.eventos}) == len(historico.eventos)
    recebidas = [l for l in linhas if l["tipo"] == "evidencia_recebida"]
    assert recebidas and all(l["simulado"] is True for l in recebidas)
    assert all(l["observacao"]["evidencia"]["documento_sha256"] for l in recebidas)
    # A fonte pode repetir o mesmo texto em sessões distintas: contar por evento.
    efeitos = [(m, p, b) for m, p, b in pedidos if m != "GET"]
    previstos = [l for l in linhas if l["tipo"] == "resultado"
                 and l["cenario"] == "memoria_automatica"
                 and l["evento"]["tipo"] in integrado.MODELO_EVENTOS | {"iniciar_sessao", "apagar_usuario"}]
    assert len(efeitos) == len(previstos)
    tentativas = [(l["cenario"], l["evento"]["id"]) for l in linhas if l["tipo"] == "tentativa"]
    assert len(tentativas) == len(set(tentativas))
    if modo == "sucesso":
        assert r["estado_orquestracao"] == "concluida"
        assert len(recebidas) == len(consultas) == 22
        assert sum(p == "/conversas" for _, p, _ in pedidos) == 53
        assert all(l.get("checkpoint") != "verificado" for l in linhas)
        assert any(l.get("checkpoint") == "verificado_simulado" for l in linhas)
    else:
        assert r["estado_orquestracao"] == "incompleta"
        assert r["motivo_interrupcao"]["evento_id"] == excluir.id
        esperado = "TimeoutEvidencia" if modo == "timeout" else "EvidenciaIncompativel"
        assert r["motivo_interrupcao"]["erro"]["tipo"] == esperado
        assert r["resultados"][-1]["evento"]["id"] == excluir.id
        assert r["resultados"][-1]["checkpoint"] == "nao_verificado"
        assert any(l["tipo"] == "rodada_interrompida" for l in linhas)
        assert all(e.id != excluir.id for e in historico.eventos)
        assert not r["avaliacao_respostas_completa"]
    # JSONL liberado e preservado; outra rodada não pode sobrescrevê-lo.
    with log.open("r+", encoding="utf-8") as f:
        assert f.readline()
    with pytest.raises(FileExistsError):
        integrado.executar(dados, clientes(), log)


@pytest.mark.parametrize("erro", ["timeout", "incompativel", "inesperado"])
def test_cli_espera_falha_retorna_um_e_fecha(dados, tmp_path, monkeypatch, erro):
    from eval.sessoes_evidencias import EvidenciaIncompativel, TimeoutEvidencia
    cs = tmp_path / "credenciais.json"
    cs.write_text("{}", encoding="utf-8")
    log = tmp_path / "cli.jsonl"
    ts = clientes()
    ts["memoria_automatica"].verificar_inicio = lambda *a, **kw: {
        "ambiente_id": "simulado", "usuarios": {u["usuario_id"]: "p6_" + u["usuario_id"] for u in dados["usuarios"]}}
    falha = {"timeout": TimeoutEvidencia, "incompativel": EvidenciaIncompativel, "inesperado": RuntimeError}[erro]
    ts["memoria_automatica"].aguardar_checkpoint = Mock(side_effect=falha("simulado"))
    monkeypatch.setattr(integrado, "TransporteHTTP", lambda *a, **kw: ts["memoria_automatica"])
    monkeypatch.setattr(integrado, "TransporteHistorico", lambda **kw: ts["historico_completo"])
    cliente = httpx.Client(transport=httpx.MockTransport(Mock(side_effect=AssertionError("Rede proibida"))))
    monkeypatch.setattr(httpx, "Client", lambda **kw: cliente)
    monkeypatch.setattr(integrado.sys, "argv", ["p6", "--executar", "--aguardar-evidencias",
                                              "--credenciais", str(cs), "--saida", str(log),
                                              "--timeout-evidencia", "2", "--intervalo-evidencia", "1"])
    assert integrado.main() == 1
    assert cliente.is_closed
    assert all(t.fechar_chamadas == 1 for t in ts.values())
    assert ler_log(log)[-1]["estado_orquestracao"] == "incompleta"
    ts["memoria_automatica"].aguardar_checkpoint.assert_called_once()


def test_inspecao_com_espera_nao_abre_transportes(monkeypatch, capsys):
    monkeypatch.setattr(integrado, "TransporteHTTP", Mock(side_effect=AssertionError("Transporte proibido")))
    monkeypatch.setattr(integrado.sys, "argv", ["p6", "--aguardar-evidencias", "--timeout-evidencia", "4",
                                              "--intervalo-evidencia", "0.5"])
    assert integrado.main() == 0
    assert json.loads(capsys.readouterr().out)["espera_evidencias"] == {
        "habilitada": True, "timeout_segundos": 4, "intervalo_segundos": .5}


@pytest.mark.parametrize("argumento,valor", [("--timeout-evidencia", "0"), ("--intervalo-evidencia", "nan"),
                                          ("--timeout-evidencia", "inf"), ("--intervalo-evidencia", "-1")])
def test_cli_recusa_prazos_invalidos(monkeypatch, argumento, valor):
    monkeypatch.setattr(integrado.sys, "argv", ["p6", argumento, valor])
    with pytest.raises(SystemExit) as erro:
        integrado.main()
    assert erro.value.code == 2



@pytest.mark.parametrize("alteracao", ["json", "ambiente", "api", "usuarios", "configuracao"])
def test_espera_rejeita_documento_incompativel(evidencia_local, relogio_evidencia, alteracao):
    from eval.sessoes_evidencias import EvidenciaIncompativel
    v, doc, salvar = evidencia_local
    if alteracao == "ambiente":
        doc["ambiente_id"] = "outro"
    elif alteracao == "api":
        doc["api_url"] = "http://outro"
    elif alteracao == "usuarios":
        doc["usuarios"]["u01"] = "p6_outro"
    elif alteracao == "configuracao":
        doc["configuracao_efetiva"]["modelo"] = "outro"
    salvar()
    if alteracao == "json":
        v.caminho.write_text("{", encoding="utf-8")
    with pytest.raises(EvidenciaIncompativel):
        v.aguardar(Evento("u01/s1/checkpoint_persistencia", "u01", 1, "checkpoint_persistencia"),
                   timeout=2, intervalo=1)
    assert not relogio_evidencia.pausas


def test_checkpoint_consume_snapshot_aceito_sem_reler_documento(evidencia_local, relogio_evidencia):
    v, doc, salvar = evidencia_local
    e = Evento("u01/s1/checkpoint_persistencia", "u01", 1, "checkpoint_persistencia")
    doc["eventos"][e.id] = evidencia_fixture(doc, e, {
        "reinicio_confirmado": True, "estado_antes": ["simulado"], "estado_depois": ["simulado"]})
    salvar()
    pedidos = []

    def responder(r):
        pedidos.append(r)
        return httpx.Response(200, json={})

    cliente = httpx.Client(base_url="http://teste", transport=httpx.MockTransport(responder))
    t = TransporteHTTP(cliente, {u: Credencial(uid, "token-falso") for u, uid in doc["usuarios"].items()},
                       verificar_checkpoint=v)
    # Barreira já exercitada pelos testes integrados; isola a fronteira de espera/consumo.
    t._pronto = True
    t._provedor, t._modelo = "ollama", "simulado"
    try:
        aceita = t.aguardar_checkpoint(e, timeout=2, intervalo=1)
        assert not pedidos
        v.caminho.write_text("{", encoding="utf-8")
        r = t.executar(e, provedor="ollama", modelo="simulado")
        assert r["evidencia"] == aceita["evidencia"]
        assert r["estado_antes"] == ["simulado"]
        assert len(pedidos) == 1 and pedidos[0].method == "GET"
        assert not t._evidencias_prontas
    finally:
        t.fechar()
    assert cliente.is_closed
