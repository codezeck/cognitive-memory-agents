import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from eval import avaliar_comparativo as comparativo
from eval.julgamento_respostas import (
    CRITERIOS, caso_para_julgamento, julgar_resposta, normalizar, resumir_julgamentos,
)

RAIZ = Path(__file__).resolve().parents[1]
DATASET = json.loads((RAIZ / "eval/dataset_comparativo.json").read_text(encoding="utf-8"))
CASOS = {c["id"]: c for c in DATASET}


def carregar_rotulos(nome):
    return json.loads((RAIZ / "eval/julgamento" / nome).read_text(encoding="utf-8"))


DEV = carregar_rotulos("respostas_dev.json")
VALIDACAO = carregar_rotulos("respostas_validacao.json")


def conferir_rotulo(item):
    caso = caso_para_julgamento(CASOS[item["caso_id"]], item.get("cenario", "memoria_regras_api"))
    resultado = julgar_resposta(item["resposta"], caso)
    assert [resultado[c]["status"] for c in CRITERIOS] == item["rotulos"]
    assert resultado["passou"] is item["passou"]
    assert resultado["protocolo_ok"] is item["protocolo_ok"]
    assert resultado["revisao_necessaria"] == ("nao_verificado" in item["rotulos"])
    for criterio, rotulo in zip(CRITERIOS, item["rotulos"]):
        assert resultado[criterio]["valor"] == {
            "aprovado": True, "reprovado": False,
            "nao_aplicavel": None, "nao_verificado": None,
        }[rotulo]


@pytest.mark.parametrize("item", DEV["casos"], ids=lambda item: item["id"])
def test_respostas_de_desenvolvimento_pre_rotuladas(item):
    conferir_rotulo(item)


@pytest.mark.parametrize("item", VALIDACAO["casos"], ids=lambda item: item["id"])
def test_respostas_de_validacao_separadas(item):
    conferir_rotulo(item)


def test_rotulos_completos_e_sem_repeticao_entre_os_conjuntos():
    for conjunto in (DEV, VALIDACAO):
        assert conjunto["criterios"] == list(CRITERIOS)
        assert len({c["id"] for c in conjunto["casos"]}) == len(conjunto["casos"])
        assert all(c["justificativa"] and c["caso_id"] in CASOS for c in conjunto["casos"])
        assert all(len(c["rotulos"]) == 4 for c in conjunto["casos"])
    assert not ({normalizar(c["resposta"]) for c in DEV["casos"]}
                & {normalizar(c["resposta"]) for c in VALIDACAO["casos"]})


def test_dataset_recebeu_somente_metadados_de_avaliacao():
    original = [{k: v for k, v in c.items() if k != "avaliacao"} for c in DATASET]
    serializado = json.dumps(original, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    assert hashlib.sha256(serializado.encode()).hexdigest() == (
        "4a524e761f0490af67c5cbfa6fcfb4f3612fd335926b7bd5ffb979fd2845dd4a"
    )


def test_anotacao_ausente_nao_aprova_nem_vira_nao_aplicavel():
    caso = copy.deepcopy(CASOS["CMP002"])
    del caso["avaliacao"]
    resultado = julgar_resposta("Campinas", caso)
    assert all(resultado[c]["status"] == "nao_verificado" for c in CRITERIOS)
    assert resultado["passou"] is False
    assert resultado["revisao_necessaria"] is True


def test_afirmacao_com_detalhes_nao_anotados_exige_revisao():
    resultado = julgar_resposta("Você mora em Campinas e gosta de música.", CASOS["CMP002"])
    assert resultado["acerto_factual"]["status"] == "nao_verificado"
    assert resultado["passou"] is False


@pytest.mark.parametrize("resposta", ["Campinas com certeza", "Certamente Campinas",
                                      "Campinas com certeza."])
def test_confirmacao_curta_acerta_conteudo_mas_nao_formato(resposta):
    resultado = julgar_resposta(resposta, CASOS["CMP002"])
    assert resultado["acerto_factual"]["status"] == "aprovado"
    assert resultado["formato_ok"]["status"] == "reprovado"
    assert resultado["passou"] is True
    assert resultado["protocolo_ok"] is False


@pytest.mark.parametrize("resposta", ["Campinas encantadora", "Campinas sem dúvida",
                                      "A bela Campinas"])
def test_frase_curta_fora_da_cobertura_nao_e_fato_comprovadamente_errado(resposta):
    resultado = julgar_resposta(resposta, CASOS["CMP002"])
    assert resultado["acerto_factual"]["status"] == "nao_verificado"
    assert resultado["formato_ok"]["status"] != "aprovado"
    assert resultado["revisao_necessaria"] is True
    assert resultado["passou"] is False


@pytest.mark.parametrize("resposta", ["Cidade desconhecida", "Ignoro sua cidade",
                                      "Não lembro", "Não recordo"])
def test_abstencao_curta_nao_coberta_exige_revisao(resposta):
    resultado = julgar_resposta(resposta, CASOS["CMP003"])
    assert resultado["acerto_factual"]["status"] == "nao_aplicavel"
    assert resultado["abstencao_correta"]["status"] == "nao_verificado"
    assert resultado["formato_ok"]["status"] == "reprovado"
    assert resultado["passou"] is False


def test_valor_composto_anotado_e_isolado_preserva_formato():
    caso = copy.deepcopy(CASOS["CMP002"])
    caso["esperado"] = "São Paulo"
    resultado = julgar_resposta("São Paulo", caso)
    assert resultado["acerto_factual"]["status"] == "aprovado"
    assert resultado["formato_ok"]["status"] == "aprovado"
    assert resultado["protocolo_ok"] is True


def test_incerteza_de_julgamento_nao_inflaciona_denominador_verificado():
    julgamentos = [julgar_resposta("Campinas", CASOS["CMP002"]),
                   julgar_resposta("Campinas encantadora", CASOS["CMP002"])]
    resumo = resumir_julgamentos([{"julgamento": j} for j in julgamentos])
    assert resumo["acerto_factual"]["verificados"] == 1
    assert resumo["acerto_factual"]["nao_verificados"] == 1


def test_lista_de_valores_nao_e_interpretada_como_abstencao():
    caso = copy.deepcopy(CASOS["CMP002"])
    caso["esperado"] = ["Campinas", "Osasco"]
    resultado = julgar_resposta("DESCONHECIDO", caso)
    assert resultado["acerto_factual"]["status"] == "nao_verificado"
    assert resultado["abstencao_correta"]["status"] == "nao_aplicavel"
    assert resultado["passou"] is False
    assert comparativo.resposta_esperada_cenario(caso, "historico_completo") != "DESCONHECIDO"


@pytest.mark.parametrize("avaliacao", [None, [], {"tipo_resposta": []},
                                        {"tipo_resposta": "factual", "atributo": []}])
def test_anotacoes_invalidas_nao_produzem_aprovacao(avaliacao):
    caso = copy.deepcopy(CASOS["CMP002"])
    caso["avaliacao"] = avaliacao
    resultado = julgar_resposta("Campinas", caso)
    assert resultado["passou"] is False
    assert resultado["acerto_factual"]["status"] == "nao_verificado"


def test_informacao_esquecida_explicita_e_usada_mesmo_sem_outras_anotacoes():
    caso = {"esperado": ["não sei"], "informacoes_esquecidas": ["Nome Sigiloso"]}
    resultado = julgar_resposta("Não sei, Nome Sigiloso.", caso)
    assert resultado["sem_informacao_proibida"]["valor"] is False
    assert resultado["passou"] is False


def test_proibidos_independem_de_fatos_e_aceitam_aliases_anotados():
    caso = copy.deepcopy(CASOS["CMP003"])
    caso["informacoes_esquecidas"] = ["São Paulo"]
    caso["avaliacao"]["aliases_proibidos"] = {"São Paulo": ["Sampa"]}
    for resposta in ("Não sei, Sampa.", "Não era São   Paulo."):
        resultado = julgar_resposta(resposta, caso)
        assert resultado["sem_informacao_proibida"]["valor"] is False
    caso = copy.deepcopy(CASOS["CMP007"])
    caso["avaliacao"]["informacoes_proibidas"] = ["Ezequiel"]
    resultado = julgar_resposta("Ezequiel", caso)
    assert resultado["acerto_factual"]["valor"] is True
    assert resultado["sem_informacao_proibida"]["valor"] is False
    assert resultado["passou"] is False


def test_limites_de_palavra_e_sem_inferencia_de_proibicao_a_partir_do_historico():
    caso = copy.deepcopy(CASOS["CMP003"])
    caso["informacoes_esquecidas"] = ["Gol"]
    assert julgar_resposta("Não sei, vi um golfinho.", caso)["sem_informacao_proibida"]["valor"] is True
    caso["informacoes_esquecidas"] = []
    resultado = julgar_resposta("Osasco", caso)
    assert resultado["sem_informacao_proibida"]["valor"] is True
    assert resultado["abstencao_correta"]["valor"] is False


def test_sem_memoria_altera_apenas_criterio_efetivo_sem_mutar_caso():
    caso = copy.deepcopy(CASOS["CMP001"])
    antes = copy.deepcopy(caso)
    efetivo = caso_para_julgamento(caso, "sem_memoria")
    assert caso == antes
    assert efetivo["mensagens"] == caso["mensagens"]
    assert julgar_resposta("DESCONHECIDO", efetivo)["passou"] is True
    assert julgar_resposta("Osasco", efetivo)["passou"] is False


@pytest.mark.parametrize("resposta", [None, 1, [], {}])
def test_ausencia_de_resposta_textual_fica_nao_verificada(resposta):
    resultado = julgar_resposta(resposta, CASOS["CMP003"])
    assert resultado["acerto_factual"]["status"] == "nao_aplicavel"
    assert resultado["abstencao_correta"]["status"] == "nao_verificado"
    assert resultado["passou"] is False


def test_resumo_expoe_cobertura_e_nao_inflaciona_privacidade_com_listas_vazias():
    julgamentos = [julgar_resposta("Campinas", CASOS["CMP002"]),
                   julgar_resposta("DESCONHECIDO", CASOS["CMP003"]),
                   julgar_resposta("Campinas", {})]
    resumo = resumir_julgamentos([
        {"julgamento": j, "protocolo_ok": j["protocolo_ok"]} for j in julgamentos
    ])
    assert resumo["acerto_factual"]["verificados"] == 1
    assert resumo["acerto_factual"]["nao_aplicaveis"] == 1
    assert resumo["acerto_factual"]["nao_verificados"] == 1
    assert resumo["sem_informacao_proibida"]["casos_considerados"] == 2
    assert resumo["sem_informacao_proibida"]["verificados"] == 1
    assert resumo["sem_informacao_proibida"]["nao_verificados"] == 1
    assert resumo["protocolo_ok"] == 2


def test_integracao_registra_dimensoes_sem_alterar_tokens_ou_despacho(monkeypatch):
    caso = copy.deepcopy(CASOS["CMP002"])
    chamadas = [{"resposta": "Registrado.", "tokens_entrada": 11, "tokens_saida": 3,
                 "latencia_ms": 1, "memorias_usadas": []} for _ in caso["mensagens"]]
    chamadas[-1]["resposta"] = "Você mora em Campinas."
    worker = Mock(return_value=chamadas)
    monkeypatch.setattr(comparativo, "executar_historico_em_processo", worker)
    cliente = Mock()
    resultado = comparativo.executar_cenario(cliente, caso, "historico_completo", "ollama", "modelo")
    worker.assert_called_once_with(caso, "ollama", "modelo", timeout=None)
    assert cliente.mock_calls == []
    assert resultado["passou"] is True
    assert resultado["protocolo_ok"] is False
    assert resultado["julgamento"]["acerto_factual"]["valor"] is True
    assert resultado["tokens_por_etapa"] == comparativo.tokens_por_etapa(chamadas)
    assert resultado["tokens_total"] == 42
    resumo = comparativo.resumir([resultado])["historico_completo"]
    assert resumo["tokens_total"] == 42
    assert resumo["julgamento"]["acerto_factual"]["verificados"] == 1
