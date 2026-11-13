import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from eval import avaliar_comparativo as comparativo
from eval.julgamento_respostas import (
    ATRIBUTOS, CRITERIOS, caso_para_julgamento, julgar_resposta, normalizar,
    resumir_julgamentos,
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


# Exemplos sintéticos de engenharia; não substituem os gabaritos oficiais P6.
NOVOS_ATRIBUTOS = [
    ("profissao", "coordenadora de enfermagem", "coordenadora", "enfermeira",
     ["Você trabalha como coordenadora de enfermagem.", "Sou coordenadora.",
      "Sua profissão atual é coordenadora de enfermagem."],
     "Você trabalha como médica.", "sua profissão"),
    ("pet", "Thor", "Thorzinho", "Luna",
     ["Meu pet se chama Thor.", "O nome do seu pet é Thor.", "Seu pet é Thorzinho."],
     "Seu pet se chama Nina.", "o nome do seu cachorro"),
    ("filhos", "três", "3", "dois",
     ["Você tem três filhos.", "Tenho 3 filhos.", "O número de seus filhos é três."],
     "Tenho quatro filhos.", "a quantidade de seus filhos"),
    ("disciplina", "matemática", "Matemática", "física",
     ["Você leciona matemática.", "Sou professor de matemática.", "Sua disciplina é matemática."],
     "Você ensina história.", "sua disciplina"),
    ("hobby", "fotografia", "fotografar", "pintura",
     ["Meu hobby é fotografia.", "Você gosta de fotografar."],
     "Seu hobby é dança.", "seu hobby"),
    ("viagem", "Portugal", "República Portuguesa", "Japão",
     ["Você vai viajar para Portugal.", "Vou para Portugal.",
      "Seu destino de viagem atual é República Portuguesa."],
     "Você viajará para Chile.", "seu destino de viagem"),
    ("quantidade_pets", "dois", "2", "um",
     ["Você tem dois pets.", "São 2 pets.", "A quantidade de seus animais de estimação é dois."],
     "Tenho três pets.", "a quantidade de seus gatos"),
    ("instrumento", "violão", "guitarra acústica", "piano",
     ["Você toca violão.", "Toco guitarra acústica.", "Meu instrumento musical é violão."],
     "Seu instrumento é flauta.", "seu instrumento musical"),
]


@pytest.fixture(params=NOVOS_ATRIBUTOS, ids=lambda v: v[0])
def atributo_p6(request):
    atributo, esperado, alias, antigo, frases, incorreta, topico = request.param
    caso = {
        "id": "sintetico-" + atributo, "categoria": "atualizacao",
        "mensagens": ["Pergunta sintética sobre o atributo anotado."],
        "esperado": esperado,
        "avaliacao": {"atributo": atributo, "tipo_resposta": "factual",
                      "aliases_aceitos": [alias], "valores_antigos": [antigo],
                      "informacoes_proibidas": []},
    }
    return caso, frases, incorreta, topico


def test_novos_atributos_aceitam_valor_alias_e_variacoes(atributo_p6):
    caso, frases, _, _ = atributo_p6
    assert caso["avaliacao"]["atributo"] in ATRIBUTOS
    comparativo.validar_dataset_p4([caso])
    antes = copy.deepcopy(caso)
    for resposta in [caso["esperado"], *caso["avaliacao"]["aliases_aceitos"], *frases]:
        r = julgar_resposta(resposta, caso)
        assert r["acerto_factual"]["valor"] is True, resposta
        assert r["passou"] is True, resposta
    assert caso == antes


def test_novos_atributos_reprovam_fato_incorreto_e_desatualizado(atributo_p6):
    caso, _, incorreta, _ = atributo_p6
    for resposta in [incorreta, *caso["avaliacao"]["valores_antigos"]]:
        r = julgar_resposta(resposta, caso)
        assert r["acerto_factual"]["valor"] is False, resposta
        assert r["passou"] is False


@pytest.mark.parametrize("modelo", ["Talvez {v}.", "Acho que {v}.", "{v} ou outro.",
                                   "Não é {v}.", "{v}?", "{v} e mais um fato."])
def test_novos_atributos_nao_aprovam_incerteza_negacao_ou_detalhes(atributo_p6, modelo):
    caso, _, _, _ = atributo_p6
    r = julgar_resposta(modelo.format(v=caso["esperado"]), caso)
    assert r["acerto_factual"]["valor"] is not True
    assert r["passou"] is False


def test_novos_atributos_abstencao_e_especulacao(atributo_p6):
    caso, frases, _, topico = atributo_p6
    caso["avaliacao"]["tipo_resposta"] = "abstencao"
    caso["esperado"] = ["DESCONHECIDO", "não sei"]
    for resposta in ["DESCONHECIDO", "Não sei.", f"Não tenho informações sobre {topico}.",
                     f"Seu histórico não contém informações sobre {topico}."]:
        r = julgar_resposta(resposta, caso)
        assert r["abstencao_correta"]["valor"] is True, resposta
        assert r["acerto_factual"]["status"] == "nao_aplicavel"
        assert r["protocolo_ok"] is (resposta == "DESCONHECIDO")
    for resposta in [frases[0], "Não sei, talvez outro valor.", "Não sei ou talvez sim."]:
        r = julgar_resposta(resposta, caso)
        assert r["abstencao_correta"]["valor"] is False, resposta
        assert r["passou"] is False


def test_novos_atributos_proibicao_independe_do_acerto(atributo_p6):
    caso, _, _, _ = atributo_p6
    caso["informacoes_esquecidas"] = [caso["esperado"]]
    caso["avaliacao"]["aliases_proibidos"] = {
        caso["esperado"]: caso["avaliacao"]["aliases_aceitos"],
    }
    for resposta in [caso["esperado"], *caso["avaliacao"]["aliases_aceitos"]]:
        r = julgar_resposta(resposta, caso)
        assert r["acerto_factual"]["valor"] is True
        assert r["sem_informacao_proibida"]["valor"] is False
        assert r["passou"] is False
    caso["avaliacao"]["tipo_resposta"] = "abstencao"
    for resposta in [f"Não sei; antes era {caso['esperado']}.",
                     f"Não é {caso['avaliacao']['aliases_aceitos'][0]}."]:
        assert julgar_resposta(resposta, caso)["sem_informacao_proibida"]["valor"] is False


def test_novos_atributos_distinguem_valor_antigo_de_proibicao(atributo_p6):
    caso, _, _, _ = atributo_p6
    antigo = caso["avaliacao"]["valores_antigos"][0]
    r = julgar_resposta(f"Antes {antigo}; agora {caso['esperado']}.", caso)
    assert r["acerto_factual"]["valor"] is True
    assert r["sem_informacao_proibida"]["valor"] is True
    assert r["formato_ok"]["valor"] is False


@pytest.mark.parametrize("atributo,valor,frase,topico", [
    ("cidade", "Campinas", "Você mora em Campinas.", "sua cidade"),
    ("esporte", "natação", "Você pratica natação.", "seu esporte"),
    ("carro", "Onix", "Seu carro é um Onix.", "seu carro"),
    ("nome", "Ana", "Seu nome é Ana.", "seu nome"),
    ("time", "Coritiba", "Você torce pelo Coritiba.", "seu time"),
])
def test_regressao_dos_cinco_atributos_originais(atributo, valor, frase, topico):
    caso = {"esperado": valor, "avaliacao": {"atributo": atributo,
            "tipo_resposta": "factual", "informacoes_proibidas": []}}
    assert julgar_resposta(frase, caso)["passou"] is True
    caso["avaliacao"]["tipo_resposta"] = "abstencao"
    assert julgar_resposta(f"Não há informações sobre {topico}.", caso)["passou"] is True
    assert julgar_resposta(frase, caso)["passou"] is False


def test_aliases_numericos_nao_sao_inventados():
    caso = {"esperado": "três", "avaliacao": {"atributo": "filhos",
            "tipo_resposta": "factual", "informacoes_proibidas": []}}
    assert julgar_resposta("3", caso)["passou"] is False
    caso["avaliacao"]["aliases_aceitos"] = ["3"]
    assert julgar_resposta("3", caso)["passou"] is True


@pytest.mark.parametrize("atributo,esperado,resposta", [
    ("pet", "Thor", "Seu gato se chama Thor."),
    ("quantidade_pets", "dois", "Você tem dois gatos."),
    ("quantidade_pets", "dois", "Você tem dois gatos e um cachorro."),
    ("filhos", "três", "Você tem três filhas."),
])
def test_qualificacoes_e_subtotais_sem_escopo_anotado_exigem_revisao(atributo, esperado, resposta):
    caso = {"esperado": esperado, "avaliacao": {"atributo": atributo,
            "tipo_resposta": "factual", "informacoes_proibidas": []}}
    r = julgar_resposta(resposta, caso)
    assert r["acerto_factual"]["status"] == "nao_verificado"
    assert r["passou"] is False
