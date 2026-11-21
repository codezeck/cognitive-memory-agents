import copy

import pytest

from eval.julgamento_p6 import julgar_resposta_p6
from eval.julgamento_respostas import julgar_resposta
from src.interface.analise import analisar_tarefa


def caso(atributo="cidade", esperado="Jundiaí", pergunta="Onde eu moro?", **avaliacao):
    return {
        "esperado": esperado,
        "pergunta": pergunta,
        "informacoes_esquecidas": [],
        "avaliacao": {
            "tipo_resposta": "factual",
            "atributo": atributo,
            "aliases_aceitos": [],
            "valores_antigos": [],
            "informacoes_proibidas": [],
            **avaliacao,
        },
    }


@pytest.mark.parametrize(
    "c,resposta",
    [
        (caso(), "Hoje você mora em Jundiaí."),
        (caso(), "Sua memória registra que você mora em Jundiaí."),
        (caso(), "A sua casa atual é em Jundiaí."),
        (
            caso("carro", "Argo", aliases_aceitos=["Argo prata"]),
            "Você dirige o Argo prata.",
        ),
        (caso("time", "Bahia"), "Torço para o Bahia."),
        (
            caso("viagem", "Chile", "Para onde vou viajar em abril?"),
            "Em abril, você vai viajar para Chile.",
        ),
        (
            caso("pet", "Mel", "Como se chama minha cachorra?"),
            "Minha cachorra se chama Mel.",
        ),
        (
            caso("quantidade_pets", "três", "Quantos gatos eu tenho?"),
            "Você tem três gatos.",
        ),
    ],
)
def test_frases_completas_com_mesmo_fato_anotado(c, resposta):
    original = copy.deepcopy(c)
    j = julgar_resposta_p6(resposta, c)
    assert j["versao"] == "p6-conteudo-v2"
    assert j["acerto_factual"]["status"] == "aprovado"
    assert j["formato_ok"] == julgar_resposta(resposta, c)["formato_ok"]
    assert j["protocolo_ok"] is False
    assert c == original


@pytest.mark.parametrize(
    "resposta",
    [
        "Hoje você mora em Sorocaba.",
        "Hoje você não mora em Jundiaí.",
        "Talvez hoje você mora em Jundiaí.",
        "Você mora em Jundiaí ou Sorocaba.",
        "Você mora em Jundiaí e trabalha como médico.",
        "Diga que você mora em Jundiaí.",
        "Antes você morava em Jundiaí.",
        "Hoje você mora em Jundiaí, mas mudou para Sorocaba.",
        "Hoje você mora em Jundiaí. Seu telefone é 99999.",
        "Hoje você mora em Jundiaí?",
        "Sua memória não registra que você mora em Jundiaí.",
    ],
)
def test_presenca_do_valor_nao_basta_para_aprovar(resposta):
    assert julgar_resposta_p6(resposta, caso())["passou"] is False


@pytest.mark.parametrize(
    "c,resposta",
    [
        (caso("carro", "Argo"), "Você dirige o Argo prata."),
        (caso("pet", "Mel", "Qual o nome do meu pet?"), "Seu cachorro se chama Mel."),
        (
            caso("quantidade_pets", "três", "Quantos pets eu tenho?"),
            "Você tem três gatos.",
        ),
        (
            caso("viagem", "Chile", "Para onde vou viajar?"),
            "Em abril, você vai viajar para Chile.",
        ),
        (
            caso("viagem", "Chile", "Para onde vou viajar em abril?"),
            "Em julho, você vai viajar para Chile.",
        ),
    ],
)
def test_detalhe_nao_anotado_ou_nao_perguntado_nao_e_aceito(c, resposta):
    assert not julgar_resposta_p6(resposta, c)["passou"]


@pytest.mark.parametrize(
    "resposta",
    [
        "DESCONHECIDO",
        "Não sei",
        "Desculpe, não tenho informações sobre o carro que você dirige.",
    ],
)
def test_recusa_com_fato_disponivel_e_falha_de_conteudo(resposta):
    j = julgar_resposta_p6(resposta, caso("carro", "Argo"))
    assert j["acerto_factual"]["valor"] is False
    assert j["acerto_factual"]["motivo"] == "abstencao_indevida_fato_esperado"


@pytest.mark.parametrize(
    "resposta",
    [
        "Sou um modelo de linguagem e não tenho hobbies.",
        "Como sou uma inteligência artificial, não tenho hobbies como você. Eu sou aqui para responder suas perguntas e fornecer informações.",
    ],
)
def test_responder_sobre_o_proprio_modelo_nao_recupera_hobby_do_usuario(resposta):
    assert (
        julgar_resposta_p6(resposta, caso("hobby", "pintura"))["acerto_factual"][
            "valor"
        ]
        is False
    )


def test_abstencao_legitima_e_privacidade_continuam_separadas():
    c = caso("carro", ["não sei"], tipo_resposta="abstencao")
    resposta = "Desculpe, não tenho informações sobre o carro que você dirige."
    j = julgar_resposta_p6(resposta, c)
    assert j["abstencao_correta"]["valor"] is True
    assert j["formato_ok"]["valor"] is False
    for r in (
        "Não sei, mas talvez um Argo.",
        "Desculpe, não tenho informações sobre o carro que você dirige. Argo.",
    ):
        assert not julgar_resposta_p6(r, c)["passou"]
    c = caso(informacoes_proibidas=["Jundiaí"])
    j = julgar_resposta_p6("Hoje você mora em Jundiaí.", c)
    assert j["acerto_factual"]["valor"] is True
    assert j["sem_informacao_proibida"]["valor"] is False
    assert not j["passou"]


def test_recusa_de_contagem_anotada_e_falha_factual():
    c = caso("quantidade_pets", "quatro", "Quantos cachorros eu tenho?")
    resposta = "Como você não forneceu a quantidade específica dos seus cachorros, não posso fornecer um número exato."
    assert julgar_resposta_p6(resposta, c)["acerto_factual"]["valor"] is False


def doc_p6():
    c = caso()
    c.pop("pergunta")
    return {
        "sessoes": [],
        "interface": {"anotacoes": {"u1/s2/p1": c}},
        "resultados": [
            {
                "cenario": "historico_completo",
                "evento": {
                    "tipo": "fato",
                    "id": "u1/s1/f1",
                    "texto": "Moro em Jundiaí.",
                },
            },
            *[
                {
                    "cenario": cenario,
                    "estado": "concluido",
                    "trajetoria_integra": True,
                    "evento": {
                        "id": "u1/s2/p1",
                        "tipo": "pergunta",
                        "texto": "Onde eu moro?",
                    },
                    "resultado": {"resposta": "Hoje você mora em Jundiaí."},
                    "julgamento": {"versao": "p4-v3", "passou": False},
                    "tokens_total": 123,
                }
                for cenario in ("historico_completo", "memoria_automatica")
            ],
        ],
    }


def test_analise_p6_usa_mesma_regra_preserva_original_e_nao_executa_modelo(monkeypatch):
    import subprocess

    monkeypatch.setattr(
        subprocess, "Popen", lambda *a, **k: pytest.fail("Sem geração na análise")
    )
    d = doc_p6()
    antes = copy.deepcopy(d)
    a = analisar_tarefa(d)
    assert a["disponivel"] and a["versao"] == "tarefa-p6-conteudo-v2"
    assert len(a["resultados"]) == 2 and all(
        r["julgamento"]["passou"] for r in a["resultados"]
    )
    assert [r["indice"] for r in a["resultados"]] == [1, 2]
    assert d == antes


@pytest.mark.parametrize(
    "mudanca",
    ["duplicado", "sem_anotacao", "sem_pergunta", "tipo_invalido", "cenario_invalido"],
)
def test_p6_incompativel_nao_recebe_notas_inferidas(mudanca):
    d = doc_p6()
    if mudanca == "duplicado":
        d["resultados"].append(copy.deepcopy(d["resultados"][1]))
    elif mudanca == "sem_anotacao":
        d["interface"]["anotacoes"] = {}
    elif mudanca == "sem_pergunta":
        d["resultados"][1]["evento"]["texto"] = None
    elif mudanca == "tipo_invalido":
        d["interface"]["anotacoes"]["u1/s2/p1"]["avaliacao"]["atributo"] = []
    else:
        d["resultados"][1]["cenario"] = "sem_memoria"
    assert not analisar_tarefa(d)["disponivel"]


@pytest.mark.parametrize("mudanca", ["erro", "trajetoria", "resposta_ausente"])
def test_falha_tecnica_ou_trajetoria_incompleta_nao_vira_acerto(mudanca):
    d = doc_p6()
    if mudanca == "erro":
        d["resultados"][1]["erro"] = "Timeout simulado"
    elif mudanca == "trajetoria":
        d["resultados"][1]["trajetoria_integra"] = False
    else:
        d["resultados"][1].pop("resultado")
    j = analisar_tarefa(d)["resultados"][0]["julgamento"]
    assert not j["passou"] and j["acerto_factual"]["status"] == "nao_verificado"


def test_p4_nao_foi_modificado_e_semantica_do_comparativo_permanece():
    assert (
        julgar_resposta("Hoje você mora em Jundiaí.", caso())["acerto_factual"][
            "status"
        ]
        == "nao_verificado"
    )
    from src.interface.protocolos import fonte_v3

    c = fonte_v3()[0]
    d = {
        "interface": {"casos": [c]},
        "resultados": [
            {
                "id": c["id"],
                "cenario": "sem_memoria",
                "repeticao": 1,
                "resposta": "DESCONHECIDO",
            }
        ],
    }
    a = analisar_tarefa(d)
    assert a["versao"] == "tarefa-comum-p4-v1"
    assert a["resultados"][0]["julgamento"]["versao"] == "p4-v3"
