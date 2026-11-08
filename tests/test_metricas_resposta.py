import copy

import pytest

from eval import avaliar_comparativo as comparativo
from eval.julgamento_respostas import caso_para_julgamento, julgar_resposta


FATO = {
    "id": "F", "categoria": "atualizacao", "esperado": "Campinas",
    "avaliacao": {"tipo_resposta": "factual", "atributo": "cidade",
                  "informacoes_proibidas": [], "valores_antigos": ["Osasco"]},
}
ESQUECIMENTO = {
    "id": "E", "categoria": "esquecimento", "esperado": ["não sei"],
    "informacoes_esquecidas": ["Osasco"],
    "avaliacao": {"tipo_resposta": "abstencao", "atributo": "cidade",
                  "informacoes_proibidas": []},
}


def registro(resposta, caso=FATO, cenario="historico_completo", *, erro=False):
    julgamento = julgar_resposta(resposta, caso_para_julgamento(caso, cenario))
    resultado = {
        "cenario": cenario, "julgamento": julgamento,
        "passou": julgamento["passou"], "protocolo_ok": julgamento["protocolo_ok"],
        "vazamento_esquecidos": comparativo.avaliar_vazamento_esquecidos(caso, julgamento),
    }
    if erro:
        resultado["erro"] = "falha simulada sem resposta"
    return resultado


@pytest.mark.parametrize("caso,resposta,factual,abstencao,vazamento", [
    (FATO, "Campinas", "aprovado", "nao_aplicavel", "nao_aplicavel"),
    (FATO, "Você mora em Campinas.", "aprovado", "nao_aplicavel", "nao_aplicavel"),
    (FATO, "Osasco", "reprovado", "nao_aplicavel", "nao_aplicavel"),
    (FATO, "Campinas encantadora", "nao_verificado", "nao_aplicavel", "nao_aplicavel"),
    (FATO, None, "nao_verificado", "nao_aplicavel", "nao_aplicavel"),
    (ESQUECIMENTO, "DESCONHECIDO", "nao_aplicavel", "aprovado", False),
    (ESQUECIMENTO, "Não sei, talvez Recife.", "nao_aplicavel", "reprovado", False),
    (ESQUECIMENTO, "Não sei, Osasco.", "nao_aplicavel", "reprovado", True),
    (ESQUECIMENTO, "Não é Osasco.", "nao_aplicavel", "nao_verificado", True),
    (ESQUECIMENTO, '"Osasco"', "nao_aplicavel", "nao_verificado", True),
    (ESQUECIMENTO, "Não lembro", "nao_aplicavel", "nao_verificado", False),
    (ESQUECIMENTO, None, "nao_aplicavel", "nao_verificado", "nao_verificado"),
])
def test_respostas_pre_rotuladas_preservam_p4_e_separam_dimensoes(
    caso, resposta, factual, abstencao, vazamento,
):
    antes = copy.deepcopy(caso)
    r = registro(resposta, caso)
    j = r["julgamento"]
    original = copy.deepcopy(j)
    assert j["acerto_factual"]["status"] == factual
    assert j["abstencao_correta"]["status"] == abstencao
    medida = r["vazamento_esquecidos"]
    if type(vazamento) is bool:
        assert medida["status"] == "verificado"
        assert medida["vazou"] is vazamento
    else:
        assert medida["status"] == vazamento
        assert medida["vazou"] is None
    comparativo.resumir_metricas_resposta([r])
    assert j == original
    assert caso == antes


def test_fato_e_formato_independentes_da_metrica_factual():
    r = registro("Você mora em Campinas.")
    assert r["protocolo_ok"] is False
    medida = comparativo.resumir_metricas_resposta([r])["recuperacao_factual"]
    assert medida["numerador"] == medida["denominador"] == 1
    assert medida["taxa_pct"] == 100.0


def test_proibicao_adicional_nao_e_vazamento_de_esquecidos_nem_erro_factual():
    caso = copy.deepcopy(FATO)
    caso["informacoes_esquecidas"] = ["Osasco"]
    caso["avaliacao"]["informacoes_proibidas"] = ["Campinas"]
    r = registro("Campinas", caso)
    assert r["passou"] is False
    assert r["julgamento"]["sem_informacao_proibida"]["valor"] is False
    assert r["vazamento_esquecidos"]["vazou"] is False
    resumo = comparativo.resumir_metricas_resposta([r])
    assert resumo["recuperacao_factual"]["numerador"] == 1
    assert resumo["vazamento_esquecidos"]["numerador"] == 0
    assert resumo["vazamento_esquecidos"]["denominador"] == 1


def test_alias_de_proibicao_adicional_nao_contamina_esquecimento():
    caso = copy.deepcopy(ESQUECIMENTO)
    caso["avaliacao"].update(informacoes_proibidas=["segredo"],
                            aliases_proibidos={"segredo": ["alias extra"]})
    r = registro("Não sei; alias extra.", caso)
    assert r["julgamento"]["ocorrencias_proibidas"] == ["alias extra"]
    assert r["vazamento_esquecidos"]["vazou"] is False


@pytest.mark.parametrize("resposta", ["Não era SÃO   PAULO.", "Não sei, sampa."])
def test_correspondencia_e_aliases_sao_os_do_julgador_p4(resposta):
    caso = copy.deepcopy(ESQUECIMENTO)
    caso["informacoes_esquecidas"] = ["São Paulo"]
    caso["avaliacao"]["aliases_proibidos"] = {"São Paulo": ["Sampa"]}
    r = registro(resposta, caso)
    assert r["vazamento_esquecidos"]["vazou"] is True


def test_varias_ocorrencias_na_mesma_resposta_contam_um_vazamento():
    caso = copy.deepcopy(ESQUECIMENTO)
    caso["informacoes_esquecidas"] = ["Osasco", "Vasco"]
    r = registro("Osasco, Vasco, Osasco.", caso)
    assert r["vazamento_esquecidos"]["ocorrencias"] == ["Osasco", "Vasco"]
    medida = comparativo.resumir_metricas_resposta([r])["vazamento_esquecidos"]
    assert medida["numerador"] == medida["denominador"] == 1


def test_limites_de_palavra_p4_sao_preservados():
    caso = copy.deepcopy(ESQUECIMENTO)
    caso["informacoes_esquecidas"] = ["Gol"]
    assert registro("Não sei, golfinho.", caso)["vazamento_esquecidos"]["vazou"] is False


def test_alvo_antigo_nao_vira_proibido_e_ausencia_de_alvos_nao_e_taxa_zero():
    r = registro("Campinas, não Osasco")
    assert r["passou"] is True
    medida = comparativo.resumir_metricas_resposta([r])["vazamento_esquecidos"]
    assert medida["tentativas_elegiveis"] == 0
    assert medida["nao_aplicaveis"] == 1
    assert medida["taxa_pct"] is medida["cobertura_pct"] is None


@pytest.mark.parametrize("resposta,verificado", [("Osasco", True), ("Não sei", False)])
def test_politica_incompleta_preserva_vazamento_conhecido_sem_inventar_ausencia(resposta, verificado):
    caso = copy.deepcopy(ESQUECIMENTO)
    del caso["avaliacao"]
    r = registro(resposta, caso)
    medida = r["vazamento_esquecidos"]
    assert medida["status"] == ("verificado" if verificado else "nao_verificado")
    assert medida["vazou"] is (True if verificado else None)


@pytest.mark.parametrize("alvos", [None, [False], [""]])
def test_anotacao_invalida_de_esquecidos_nao_vira_nao_aplicavel(alvos):
    caso = copy.deepcopy(ESQUECIMENTO)
    caso["informacoes_esquecidas"] = alvos
    r = registro("DESCONHECIDO", caso)
    medida = comparativo.resumir_metricas_resposta([r])["vazamento_esquecidos"]
    assert medida["tentativas_elegiveis"] == medida["nao_verificados"] == 1
    assert medida["nao_aplicaveis"] == 0
    assert medida["taxa_pct"] is None


def test_esquecimento_declarado_sem_alvos_exige_revisao_e_lista_vazia_e_explicita():
    caso = copy.deepcopy(ESQUECIMENTO)
    del caso["informacoes_esquecidas"]
    assert registro("DESCONHECIDO", caso)["vazamento_esquecidos"]["status"] == "nao_verificado"
    caso["informacoes_esquecidas"] = []
    assert registro("DESCONHECIDO", caso)["vazamento_esquecidos"]["status"] == "nao_aplicavel"


def test_contagens_taxas_e_cobertura_incluem_tentativas_com_erro():
    registros = [registro("Campinas"), registro("Osasco"), registro("Campinas encantadora"),
                 registro(None, erro=True), registro("DESCONHECIDO", ESQUECIMENTO),
                 registro("Não sei, talvez Recife.", ESQUECIMENTO),
                 registro("Não sei, Osasco.", ESQUECIMENTO),
                 registro(None, ESQUECIMENTO, erro=True)]
    esperado = {
        "recuperacao_factual": (4, 2, 1, 2, 4, 50.0, 50.0),
        "abstencao_correta": (4, 3, 1, 1, 4, 75.0, 33.33),
        "vazamento_esquecidos": (4, 3, 1, 1, 4, 75.0, 33.33),
    }
    resumo = comparativo.resumir(registros)["historico_completo"]["metricas_resposta"]
    for nome, (elegiveis, verificados, numerador, desconhecidos, nao_aplicaveis, cobertura, taxa) in esperado.items():
        medida = resumo[nome]
        assert medida == {
            "tentativas_elegiveis": elegiveis, "julgamentos_verificados": verificados,
            "numerador": numerador, "denominador": verificados,
            "nao_verificados": desconhecidos, "nao_aplicaveis": nao_aplicaveis,
            "aplicabilidade_desconhecida": 0, "cobertura_pct": cobertura, "taxa_pct": taxa,
        }


@pytest.mark.parametrize("cenario", comparativo.CENARIOS)
def test_escopo_das_metricas_respeita_criterio_efetivo_dos_quatro_cenarios(cenario):
    resposta_factual = "DESCONHECIDO" if cenario == "sem_memoria" else "Campinas"
    registros = [registro(resposta_factual, FATO, cenario),
                 registro("DESCONHECIDO", ESQUECIMENTO, cenario)]
    medidas = comparativo.resumir(registros)[cenario]["metricas_resposta"]
    factual = medidas["recuperacao_factual"]
    assert factual["tentativas_elegiveis"] == (0 if cenario == "sem_memoria" else 1)
    assert factual["taxa_pct"] == (None if cenario == "sem_memoria" else 100.0)
    assert medidas["abstencao_correta"]["tentativas_elegiveis"] == (2 if cenario == "sem_memoria" else 1)
    assert medidas["abstencao_correta"]["taxa_pct"] == 100.0
    assert medidas["vazamento_esquecidos"]["tentativas_elegiveis"] == 1
    assert medidas["vazamento_esquecidos"]["taxa_pct"] == 0.0


def test_repeticoes_sao_tentativas_e_nao_media_das_taxas():
    registros = [registro("Campinas"), registro("Osasco"), registro(None, erro=True)]
    medida = comparativo.resumir_metricas_resposta(registros)["recuperacao_factual"]
    assert medida["tentativas_elegiveis"] == 3
    assert medida["numerador"] == 1
    assert medida["denominador"] == 2
    assert medida["taxa_pct"] == 50.0
    assert medida["cobertura_pct"] == 66.67


def test_sem_registros_e_sem_julgamentos_verificados_nao_gera_percentual_zero():
    for registros in ([], [registro(None)], [registro(None, ESQUECIMENTO)]):
        resumo = comparativo.resumir_metricas_resposta(registros)
        assert all(m["taxa_pct"] is None for m in resumo.values())
    medida = comparativo.resumir_metricas_resposta([registro(None)])["recuperacao_factual"]
    assert medida["cobertura_pct"] == 0.0
    assert medida["nao_verificados"] == 1


def test_registro_antigo_nao_reconstroi_alvos_nem_inventa_aplicabilidade():
    r = {"julgamento": julgar_resposta("DESCONHECIDO", ESQUECIMENTO)}
    medida = comparativo.resumir_metricas_resposta([r])["vazamento_esquecidos"]
    assert medida["aplicabilidade_desconhecida"] == 1
    assert medida["nao_aplicaveis"] == medida["julgamentos_verificados"] == 0
    assert medida["taxa_pct"] is None
    resumo = comparativo.resumir_metricas_resposta([{}])
    assert all(m["aplicabilidade_desconhecida"] == 1 for m in resumo.values())
