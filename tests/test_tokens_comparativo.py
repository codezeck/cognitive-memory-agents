import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from eval import avaliar_comparativo as comparativo


def chamada(entrada, saida):
    return {"tokens_entrada": entrada, "tokens_saida": saida, "latencia_ms": 1,
            "resposta": "Osasco", "memorias_usadas": []}


def registro(cenario, entrada=100, saida=10, *, identificador="A", repeticao=1,
             provedor="ollama", modelo="modelo-simulado", ingestao=()):
    chamadas = [*ingestao, chamada(entrada, saida)]
    return {
        "id": identificador, "repeticao": repeticao, "cenario": cenario,
        "provedor": provedor, "modelo": modelo, "passou": True,
        **comparativo.metricas(chamadas),
        "tokens_por_etapa": comparativo.tokens_por_etapa(chamadas),
    }


def test_etapas_separam_entrada_saida_e_recompoem_sessao():
    etapas = comparativo.tokens_por_etapa([
        chamada(100, 10), chamada(200, 20), chamada(300, 30),
    ])
    for etapa, entrada, saida, quantidade in (
        ("ingestao", 300, 30, 2), ("pergunta_final", 300, 30, 1),
        ("sessao", 600, 60, 3),
    ):
        assert etapas[etapa]["tokens_entrada"] == entrada
        assert etapas[etapa]["tokens_saida"] == saida
        assert etapas[etapa]["tokens_total"] == entrada + saida
        assert etapas[etapa]["chamadas_modelo"] == quantidade
        assert etapas[etapa]["metricas_completas"] is True


def test_contagens_parciais_sao_preservadas_sem_inventar_total():
    dados = comparativo.metricas([chamada(10, None)])
    assert dados["tokens_entrada"] == 10
    assert dados["tokens_saida"] is None
    assert dados["tokens_total"] is None
    assert dados["tokens_total_observados"] == 10
    assert dados["metricas_completas"] is False

    etapas = comparativo.tokens_por_etapa([
        chamada(10, None), chamada(None, 3), chamada(20, 2),
    ])
    sessao = etapas["sessao"]
    assert sessao["tokens_entrada"] is None
    assert sessao["tokens_saida"] is None
    assert sessao["tokens_entrada_observados"] == 30
    assert sessao["tokens_saida_observados"] == 5
    assert sessao["tokens_total_observados"] == 35
    assert etapas["pergunta_final"]["tokens_total"] == 22


@pytest.mark.parametrize("valor", [None, -1, True, 1.5, "7"])
def test_metadado_ausente_ou_invalido_nao_vira_zero(valor):
    dados = comparativo.tokens_etapa([chamada(valor, 2)])
    assert dados["tokens_entrada"] is None
    assert dados["tokens_entrada_observados"] is None
    assert dados["tokens_saida"] == 2
    assert dados["tokens_total"] is None


def test_sem_chamadas_e_diferente_de_medicao_desconhecida():
    sem_ingestao = comparativo.tokens_por_etapa([chamada(10, 2)])["ingestao"]
    assert sem_ingestao["tokens_total"] == 0
    assert sem_ingestao["chamadas_modelo"] == 0
    assert sem_ingestao["metricas_completas"] is True
    for etapas in (comparativo.tokens_por_etapa(None), comparativo.tokens_por_etapa([])):
        for medida in etapas.values():
            assert medida["tokens_total"] is None
            assert medida["tokens_total_observados"] is None
            assert medida["chamadas_modelo"] is None


def test_zero_reportado_e_sinalizado_sem_inventar_medicao_completa():
    dados = comparativo.tokens_etapa([chamada(0, 2)])
    assert dados["tokens_entrada"] is None
    assert dados["tokens_saida"] == 2
    assert dados["tokens_total"] is None
    assert dados["tokens_total_observados"] == 2
    assert dados["metricas_completas"] is False
    assert dados["chamadas_com_tokens_zero"] == 1
    assert dados["chamadas_com_entrada_zero_nao_verificado"] == 1


def test_tentativa_parcial_preserva_parcelas_sem_contar_chamadas_faltantes_como_zero():
    recebidas = [chamada(11, 3)]
    etapas = comparativo.tokens_tentativa(
        {"mensagens": ["Fato 1", "Fato 2", "Pergunta"]},
        "memoria_regras_api", recebidas,
    )
    assert etapas["ingestao"]["tokens_total"] is None
    assert etapas["ingestao"]["tokens_total_observados"] == 14
    assert etapas["sessao"]["tokens_total"] is None
    assert etapas["sessao"]["tokens_total_observados"] == 14
    assert etapas["sessao"]["chamadas_modelo"] is None
    assert etapas["sessao"]["chamadas_observadas"] == 1
    assert etapas["sessao"]["chamadas_previstas"] == 3
    assert etapas["pergunta_final"]["tokens_total_observados"] is None
    assert len(recebidas) == 1


def test_api_preserva_chamada_recebida_e_repassa_o_mesmo_erro(monkeypatch):
    erro = TimeoutError("falha simulada no segundo turno")
    monkeypatch.setattr(comparativo, "limpar_usuario", lambda cliente: None)
    monkeypatch.setattr(comparativo, "conversar", Mock(side_effect=[chamada(11, 3), erro]))
    observacao = {}
    with pytest.raises(TimeoutError) as captura:
        comparativo.executar_cenario(
            Mock(), {"id": "PARCIAL", "categoria": "recuperacao", "esperado": "Osasco",
                     "mensagens": ["Fato 1", "Fato 2", "Pergunta"]},
            "memoria_regras_api", "ollama", "modelo-simulado",
            observacao_tokens=observacao,
        )
    assert captura.value is erro
    assert observacao["sessao"]["tokens_total"] is None
    assert observacao["sessao"]["tokens_total_observados"] == 14


def test_resumo_inclui_reprovacoes_e_expoe_denominador_e_custo_desconhecido():
    a = registro("historico_completo", 10, 2)
    b = registro("historico_completo", 20, 4, identificador="B")
    b["passou"] = False
    erro = {"cenario": "historico_completo", "passou": False, "erro": "Timeout",
            "tokens_por_etapa": comparativo.tokens_por_etapa(None)}
    resumo = comparativo.resumir([a, b, erro])["historico_completo"]
    medida = resumo["tokens_por_etapa"]["sessao"]
    assert resumo["tokens_total"] is None
    assert medida["tokens_total_observados"] == 36
    assert medida["casos_tentados"] == 3
    assert medida["casos_medidos"] == 2
    assert medida["casos_desconhecidos"] == 1
    assert medida["media_tokens_total_por_caso_medido"] == 18


def test_resumo_preserva_canal_completo_e_parcelas_de_casos_incompletos():
    a = registro("historico_completo", 10, 2)
    b = registro("historico_completo", 20, None, ingestao=[chamada(None, 3)])
    medida = comparativo.resumir([a, b])["historico_completo"]["tokens_por_etapa"]["sessao"]
    assert medida["tokens_entrada"] is None
    assert medida["tokens_entrada_observados"] == 30
    assert medida["tokens_saida_observados"] == 5
    assert medida["tokens_total_observados"] == 35
    assert medida["casos_medidos"] == 1
    assert medida["casos_desconhecidos"] == 1
    finais = comparativo.resumir([a, b])["historico_completo"]["tokens_por_etapa"]["pergunta_final"]
    assert finais["tokens_entrada"] == 30
    assert finais["tokens_saida"] is None


def test_sem_medicoes_ou_sem_casos_resumo_nao_apresenta_custo_zero():
    for resultados in ([], [{"cenario": "historico_completo", "erro": "Falha"}]):
        medida = comparativo.resumir(resultados)["historico_completo"]["tokens_por_etapa"]["sessao"]
        assert medida["tokens_total"] is None
        assert medida["tokens_total_observados"] is None
        assert medida["media_tokens_total_por_caso_medido"] is None


def test_comparacao_usa_mesmos_pares_por_canal_sem_filtrar_aprovacao():
    resultados = [
        registro("historico_completo", 100, 10),
        registro("historico_completo", 200, 20, repeticao=2),
        registro("memoria_regras_api", 40, 5),
        registro("memoria_regras_api", 100, None, repeticao=2),
        registro("memoria_regras_api", 1, 1, repeticao=3),
        registro("memoria_regras_api", 1, 1, identificador="B"),
        registro("memoria_regras_api", 1, 1, provedor="outro"),
        registro("memoria_regras_api", 1, 1, modelo="outro"),
    ]
    resultados[2]["passou"] = False
    dados = comparativo.comparar_tokens(resultados)["memoria_regras_api"]["pergunta_final"]
    entrada = dados["tokens_entrada"]
    assert entrada["pares_medidos"] == 2
    assert entrada["tokens_historico"] == 300
    assert entrada["tokens_cenario"] == 140
    assert entrada["reducao_pct"] == 53.33
    assert dados["tokens_saida"]["pares_medidos"] == 1
    assert dados["tokens_saida"]["reducao_pct"] == 50
    assert dados["tokens_total"]["pares_medidos"] == 1
    assert dados["tokens_total"]["pares_sem_medicao"] == 1
    assert dados["tokens_total"]["reducao_pct"] == 59.09
    assert entrada["casos_repeticoes"] == [
        {"id": "A", "repeticao": n, "provedor": "ollama", "modelo": "modelo-simulado"}
        for n in (1, 2)
    ]


def test_comparacao_descarta_chaves_duplicadas_sem_escolher_resultado_favoravel():
    dados = comparativo.comparar_tokens([
        registro("historico_completo"), registro("historico_completo"),
        registro("memoria_regras_api"),
    ])["memoria_regras_api"]["pergunta_final"]["tokens_total"]
    assert dados["pares_identificados"] == 1
    assert dados["chaves_duplicadas_descartadas"] == 1
    assert dados["pares_medidos"] == 0
    assert dados["tokens_historico"] is None
    assert dados["reducao_pct"] is None


@pytest.mark.parametrize("repeticao", [None, 0, True, "1"])
def test_repeticao_nao_identificada_nao_e_pareada(repeticao):
    resultados = [registro(c, repeticao=repeticao)
                  for c in ("historico_completo", "memoria_regras_api")]
    dados = comparativo.comparar_tokens(resultados)["memoria_regras_api"]["sessao"]["tokens_total"]
    assert dados["pares_medidos"] == 0
    assert dados["reducao_pct"] is None


def test_denominador_zero_e_pares_ausentes_nao_produzem_economia():
    resultados = [registro(c, 0, 0)
                  for c in ("historico_completo", "memoria_regras_api")]
    for dados in (comparativo.comparar_tokens(resultados), comparativo.comparar_tokens([])):
        medida = dados["memoria_regras_api"]["sessao"]["tokens_total"]
        assert medida["reducao_pct"] is None


def test_controles_sem_aquisicao_nao_recebem_comparacao_de_sessao_completa():
    dados = comparativo.comparar_tokens([])
    assert set(dados["memoria_persistente_api"]) == {"pergunta_final"}
    assert set(dados["sem_memoria"]) == {"pergunta_final"}
    assert set(dados["memoria_regras_api"]) == set(comparativo.ETAPAS_TOKENS)


def test_etapa_medida_antes_de_erro_continua_comparavel():
    base = registro("historico_completo", ingestao=[chamada(100, 10)])
    candidato = registro("memoria_regras_api", ingestao=[chamada(40, 5)])
    candidato["erro"] = "Falha após a resposta do modelo"
    dados = comparativo.comparar_tokens([base, candidato])["memoria_regras_api"]
    assert dados["ingestao"]["tokens_total"]["pares_medidos"] == 1
    assert dados["ingestao"]["tokens_total"]["tokens_cenario"] == 45


@pytest.mark.parametrize("cenario", comparativo.CENARIOS)
def test_cenarios_registram_etapas_e_preparacao_sem_alterar_execucao(monkeypatch, cenario):
    caso = {"id": "P3", "categoria": "recuperacao", "mensagens": ["Fato 1", "Fato 2", "Pergunta"],
            "esperado": "Osasco", "memorias": ["Fato A", "Fato B"],
            "estado_regras_esperado": {}}
    saida = chamada(11, 3)
    if cenario == "sem_memoria":
        saida["resposta"] = "DESCONHECIDO"
    monkeypatch.setattr(comparativo, "limpar_usuario", lambda cliente: None)
    monkeypatch.setattr(comparativo, "conversar", lambda *args: dict(saida))
    monkeypatch.setattr(comparativo, "iniciar_nova_sessao", lambda cliente: None)
    monkeypatch.setattr(comparativo, "obter_estado_regras", lambda cliente: {})
    criar = Mock(return_value="id-simulado")
    monkeypatch.setattr(comparativo, "criar_memoria", criar)
    monkeypatch.setattr(comparativo, "executar_historico_em_processo",
                        lambda *args, **kwargs: [dict(saida) for _ in caso["mensagens"]])

    resultado = comparativo.executar_cenario(Mock(), caso, cenario, "ollama", "modelo-simulado")
    ingestao = 2 if cenario in {"historico_completo", "memoria_regras_api"} else 0
    assert resultado["tokens_por_etapa"]["ingestao"]["tokens_total"] == 14 * ingestao
    assert resultado["tokens_por_etapa"]["pergunta_final"]["tokens_total"] == 14
    assert resultado["tokens_por_etapa"]["sessao"]["tokens_total"] == 14 * (ingestao + 1)
    assert resultado["preparacao"]["custo_total_sistema_medido"] is False
    if cenario == "memoria_persistente_api":
        assert resultado["preparacao"]["tipo"] == "estado_ouro_pre_carregado"
        assert resultado["preparacao"]["custo_obtencao_estado_ouro"] == "nao_medido"
        assert resultado["preparacao"]["memorias_previstas"] == criar.call_count == 2


def test_main_registra_falhas_como_custo_desconhecido(monkeypatch, tmp_path, capsys):
    caso = {"id": "P3", "categoria": "recuperacao", "mensagens": ["Pergunta"],
            "esperado": "Osasco", "memorias": []}
    dataset = Mock()
    dataset.read_text.return_value = json.dumps([caso])
    dataset.relative_to.return_value = Path("eval/dataset_simulado.json")
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.get.return_value.json.return_value = {"status": "ok"}
    monkeypatch.setattr(comparativo.httpx, "Client", lambda **kwargs: cliente)
    monkeypatch.setattr(comparativo, "DATASET", dataset)
    monkeypatch.setattr(comparativo, "carregar_token", lambda: "token-simulado")
    monkeypatch.setattr(comparativo, "executar_cenario", Mock(side_effect=TimeoutError("simulado")))
    saida = tmp_path / "resultado.json"
    monkeypatch.setattr(comparativo.sys, "argv", ["avaliar_comparativo", "--saida", str(saida)])

    assert comparativo.main() == 0
    documento = json.loads(saida.read_text(encoding="utf-8"))
    for r in documento["resultados"]:
        assert r["tokens_total"] is None
        assert r["tokens_por_etapa"]["ingestao"]["tokens_total"] == 0
        assert r["tokens_por_etapa"]["pergunta_final"]["tokens_total"] is None
        assert r["tokens_por_etapa"]["sessao"]["tokens_total"] is None
    for resumo in documento["resumo"].values():
        assert resumo["tokens_total"] is None
        assert resumo["tokens_por_etapa"]["sessao"]["casos_desconhecidos"] == 1
    assert "comparacoes_tokens" in documento
    assert "tokens=desconhecido" in capsys.readouterr().out


@pytest.mark.parametrize("lado", ["historico_completo", "memoria_regras_api"])
@pytest.mark.parametrize("entrada,saida,afetado,preservado", [
    (0, 5, "tokens_entrada", "tokens_saida"),
    (50, 0, "tokens_saida", "tokens_entrada"),
])
def test_zero_sem_origem_verificavel_exclui_somente_canais_afetados(
    lado, entrada, saida, afetado, preservado,
):
    resultados = [registro(c) for c in ("historico_completo", "memoria_regras_api")]
    resultados[0 if lado == "historico_completo" else 1] = registro(lado, entrada, saida)
    dados = comparativo.comparar_tokens(resultados)["memoria_regras_api"]["pergunta_final"]
    for campo in (afetado, "tokens_total"):
        assert dados[campo]["pares_medidos"] == 0
        assert dados[campo]["pares_sem_medicao"] == 1
        assert dados[campo]["reducao_pct"] is None
    assert dados[preservado]["pares_medidos"] == 1


def test_zero_ambiguo_em_uma_chamada_preserva_parcelas_positivas_da_sessao():
    medida = comparativo.tokens_etapa([chamada(10, 3), chamada(0, 2)])
    assert medida["tokens_entrada"] is None
    assert medida["tokens_entrada_observados"] == 10
    assert medida["tokens_saida"] == 5
    assert medida["tokens_total"] is None
    assert medida["tokens_total_observados"] == 15


@pytest.mark.parametrize("entrada,saida", [(0, 0), (0, 5), (50, 0)])
def test_comparacao_recusa_tambem_zeros_ambiguos_em_resultados_legados(entrada, saida):
    base = registro("historico_completo")
    candidato = registro("memoria_regras_api")
    candidato["tokens_por_etapa"]["pergunta_final"] = {
        "tokens_entrada": entrada, "tokens_saida": saida,
        "tokens_total": entrada + saida, "chamadas_modelo": 1,
        "metricas_completas": True, "chamadas_com_tokens_zero": 1,
    }
    dados = comparativo.comparar_tokens([base, candidato])["memoria_regras_api"]["pergunta_final"]
    assert all(m["reducao_pct"] is None for m in dados.values())


def test_uso_ausente_no_adaptador_simulado_nao_vira_economia():
    from types import SimpleNamespace
    from src.modelos.ollama_adapter import OllamaAdapter

    adaptador = object.__new__(OllamaAdapter)
    adaptador.modelo = "modelo-simulado"
    adaptador.cliente = Mock()
    adaptador.cliente.chat.return_value = SimpleNamespace(
        message=SimpleNamespace(content="Osasco"),
    )
    resposta = adaptador.gerar_com_detalhes([{"role": "user", "content": "Pergunta"}])
    assert resposta["tokens_entrada"] == resposta["tokens_saida"] == 0
    base = registro("historico_completo")
    candidato = registro("memoria_regras_api", resposta["tokens_entrada"], resposta["tokens_saida"])
    dados = comparativo.comparar_tokens([base, candidato])["memoria_regras_api"]["pergunta_final"]
    assert all(m["reducao_pct"] is None for m in dados.values())
    resumo = comparativo.resumir([candidato])["memoria_regras_api"]
    assert resumo["tokens_total"] is None
    assert resumo["tokens_por_etapa"]["sessao"]["casos_com_tokens_zero"] == 1


@pytest.mark.parametrize("cenario", comparativo.CENARIOS)
def test_falha_sem_resposta_preserva_ingestao_comprovadamente_sem_chamadas(cenario):
    caso = {"mensagens": ["Fato", "Pergunta"]}
    etapas = comparativo.tokens_tentativa(caso, cenario, [])
    ingestao = etapas["ingestao"]
    if cenario in {"sem_memoria", "memoria_persistente_api"}:
        assert ingestao["tokens_entrada"] == ingestao["tokens_saida"] == ingestao["tokens_total"] == 0
        assert ingestao["chamadas_previstas"] == ingestao["chamadas_observadas"] == 0
        assert ingestao["chamadas_modelo"] == 0
    else:
        assert ingestao["tokens_total"] is None
        assert ingestao["chamadas_modelo"] is None
    assert etapas["pergunta_final"]["tokens_total"] is None
    assert etapas["sessao"]["tokens_total"] is None


def test_ingestao_vazia_continua_sendo_medicao_comparavel():
    resultados = [registro(c) for c in ("historico_completo", "memoria_regras_api")]
    dados = comparativo.comparar_tokens(resultados)["memoria_regras_api"]["ingestao"]["tokens_total"]
    assert dados["pares_medidos"] == 1
    assert dados["tokens_historico"] == dados["tokens_cenario"] == 0
    assert dados["reducao_pct"] is None


def test_terminal_usa_mesmo_denominador_da_taxa_com_falhas(monkeypatch, tmp_path, capsys):
    caso = {"id": "SIMULADO", "categoria": "recuperacao", "mensagens": ["Pergunta"],
            "esperado": "Osasco", "memorias": []}
    dataset = Mock()
    dataset.read_text.return_value = json.dumps([caso])
    dataset.relative_to.return_value = Path("eval/dataset_simulado.json")
    cliente = MagicMock()
    cliente.__enter__.return_value = cliente
    cliente.get.return_value.json.return_value = {"status": "ok"}
    monkeypatch.setattr(comparativo.httpx, "Client", lambda **kwargs: cliente)
    monkeypatch.setattr(comparativo, "DATASET", dataset)
    monkeypatch.setattr(comparativo, "carregar_token", lambda: "token-simulado")
    tentativas = {}

    def executar(cliente, caso, cenario, provedor, modelo, **kwargs):
        tentativas[cenario] = tentativas.get(cenario, 0) + 1
        if tentativas[cenario] == 2:
            raise TimeoutError("falha simulada")
        return {**registro(cenario), "resposta": "Osasco"}

    monkeypatch.setattr(comparativo, "executar_cenario", executar)
    saida = tmp_path / "resultado.json"
    monkeypatch.setattr(comparativo.sys, "argv", ["avaliar_comparativo", "--repeticoes", "2",
                                                "--saida", str(saida)])
    assert comparativo.main() == 0
    terminal = capsys.readouterr().out
    for cenario in comparativo.CENARIOS:
        assert f"{cenario}: 1/2 acertos (50.0%) | execuções concluídas=1; falhas=1" in terminal
    documento = json.loads(saida.read_text(encoding="utf-8"))
    assert all(r["casos"] == 2 and r["taxa_aprovacao_pct"] == 50.0
               for r in documento["resumo"].values())
